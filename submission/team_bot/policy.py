"""Offline deterministic soccer planner. No simulator imports at inference."""
from __future__ import annotations
import heapq
import json
import math
from pathlib import Path

DIRECTIONS = {'STAY': (0.,0.), 'UP': (0.,1.), 'UP_RIGHT': (2**-.5,2**-.5),
              'RIGHT': (1.,0.), 'DOWN_RIGHT': (2**-.5,-2**-.5), 'DOWN': (0.,-1.),
              'DOWN_LEFT': (-2**-.5,-2**-.5), 'LEFT': (-1.,0.), 'UP_LEFT': (-2**-.5,2**-.5)}

def distance(a,b):
    return math.hypot(a[0]-b[0],a[1]-b[1])

def hits(p,r,o):
    x,y,w,h=o
    if p[0]<=x-r or p[0]>=x+w+r or p[1]<=y-r or p[1]>=y+h+r:
        return False
    return (p[0]-min(max(p[0],x),x+w))**2+(p[1]-min(max(p[1],y),y+h))**2 < r*r

class Arena:
    def __init__(self,obs,settings):
        s=obs['state']; f=s['field']
        self.w,self.h=float(f['width']),float(f['height'])
        self.pr=float(f.get('player_radius',3)); self.speed=float(f.get('player_speed',4))
        self.br=settings['ball_radius']; self.bs=settings['ball_speed']
        self.gw=float(f.get('goal_width',36))
        self.rects=[(o['x'],o['y'],o['width'],o['height']) for o in s.get('obstacles',[])]

    def valid(self,p):
        r=self.pr
        return r<=p[0]<=self.w-r and r<=p[1]<=self.h-r and not any(hits(p,r,o) for o in self.rects)

    def segment(self,a,b):
        r=self.pr+.3; dx,dy=b[0]-a[0],b[1]-a[1]
        for x,y,w,h in self.rects:
            lo,hi=0.,1.
            for origin,delta,lower,upper in ((a[0],dx,x-r,x+w+r),(a[1],dy,y-r,y+h+r)):
                if abs(delta)<1e-12:
                    if not lower<origin<upper:
                        lo,hi=2.,1.; break
                else:
                    t1,t2=(lower-origin)/delta,(upper-origin)/delta
                    lo,hi=max(lo,min(t1,t2)),min(hi,max(t1,t2))
            if lo<hi and hi>0 and lo<1: return False
        return True

    def trajectory(self,origin,direction,remaining):
        """Ball-only forecast with official substep size and rebound geometry."""
        x,y=origin; vx,vy=direction; result=[]; frame=0
        while remaining>1e-9 and frame<64:
            frame+=1; travel=min(self.bs,remaining)
            n=max(1,math.ceil(travel/max(.25,self.br*.45))); step=travel/n
            for j in range(n):
                nx,ny=x+vx*step,y+vy*step
                if (self.w-self.gw)/2<=nx<=(self.w+self.gw)/2:
                    if ny+self.br>=self.h:
                        result.append(((nx,ny),frame,1)); return result
                    if ny-self.br<=0:
                        result.append(((nx,ny),frame,-1)); return result
                if nx<self.br or nx>self.w-self.br:
                    vx=-vx; nx=min(max(nx,self.br),self.w-self.br)
                if ny<self.br or ny>self.h-self.br:
                    vy=-vy; ny=min(max(ny,self.br),self.h-self.br)
                for ox,oy,ow,oh in self.rects:
                    if hits((nx,ny),self.br,(ox,oy,ow,oh)):
                        cx=x<=ox-self.br or x>=ox+ow+self.br
                        cy=y<=oy-self.br or y>=oy+oh+self.br
                        if cx: vx=-vx
                        if cy: vy=-vy
                        if not cx and not cy: vx,vy=-vx,-vy
                        nx,ny=x+vx*min(.05,self.br/10),y+vy*min(.05,self.br/10)
                        break
                x,y=nx,ny; remaining=max(0.,remaining-step)
                result.append(((x,y),frame-1+(j+1)/n,0))
        return result

class Navigator:
    def __init__(self,arena):
        self.arena=arena; r=arena.pr+.45; self.nodes=[]
        for x,y,w,h in arena.rects:
            for p in ((x-r,y-r),(x-r,y+h+r),(x+w+r,y-r),(x+w+r,y+h+r)):
                if arena.valid(p): self.nodes.append(p)
        self.edges=[[] for _ in self.nodes]
        for i,a in enumerate(self.nodes):
            for j in range(i):
                b=self.nodes[j]
                if arena.segment(a,b):
                    d=distance(a,b); self.edges[i].append((j,d)); self.edges[j].append((i,d))

    def routes(self,target):
        costs=[float('inf')]*len(self.nodes); queue=[]
        for i,p in enumerate(self.nodes):
            if self.arena.segment(p,target):
                costs[i]=distance(p,target); heapq.heappush(queue,(costs[i],i))
        while queue:
            d,i=heapq.heappop(queue)
            if d!=costs[i]: continue
            for j,edge in self.edges[i]:
                nd=d+edge
                if nd<costs[j]:
                    costs[j]=nd; heapq.heappush(queue,(nd,j))
        return target,costs

    def cost(self,p,route):
        target,costs=route
        best=distance(p,target) if self.arena.segment(p,target) else float('inf')
        for node,c in zip(self.nodes,costs):
            if c<best and self.arena.segment(p,node): best=min(best,distance(p,node)+c)
        return best

class Policy:
    def __init__(self,settings):
        self.settings=settings; self.cache_key=None; self.arena=None; self.nav=None

    @classmethod
    def load(cls,path: Path):
        settings=json.loads(path.read_text(encoding='utf-8'))
        if settings.get('format')!='torpedo-planner-v1': raise ValueError('Unexpected planner configuration')
        return cls(settings)

    def choose_action(self,obs):
        s=obs['state']; f=s['field']; ball=s['ball']
        me_id=obs['player_id']; enemy_id=obs['opponent_id']
        me=(s['players'][me_id]['x'],s['players'][me_id]['y'])
        enemy=(s['players'][enemy_id]['x'],s['players'][enemy_id]['y'])
        sign=1 if obs['attack_direction']=='UP' else -1
        key=(tuple(sorted(f.items())),tuple(tuple(sorted(o.items())) for o in s.get('obstacles',[])))
        if key!=self.cache_key:
            self.arena=Arena(obs,self.settings); self.nav=Navigator(self.arena); self.cache_key=key
        a=self.arena; nav=self.nav; moves=[]
        for name in obs['action_space']['move']:
            if name not in DIRECTIONS: continue
            dx,dy=DIRECTIONS[name]; p=(me[0]+dx*a.speed,me[1]+dy*a.speed)
            if a.valid(p): moves.append((name,p))
        if not moves: return {'move':'STAY'}
        owner=ball['possession']
        if owner==me_id: return self.attack(obs,me,enemy,moves,sign)
        target=(ball['x'],ball['y'])
        if ball['status']=='moving':
            v=ball.get('velocity',{}); vx,vy=v.get('x',0),v.get('y',0); length=math.hypot(vx,vy)
            if length:
                path=a.trajectory(target,(vx/length,vy/length),ball['remaining_kick_distance'])
                # Movement happens before the ball: select an actual first-frame
                # interception instead of steering only toward an endpoint.
                catches=[]
                for name,p in moves:
                    for point,t,goal in path:
                        if t>1 or goal: break
                        if distance(point,p)<=a.pr+a.br:
                            catches.append((t,distance(p,enemy),name)); break
                if catches:
                    catches.sort(key=lambda item:(item[0],-item[1]))
                    return {'move':catches[0][2]}
                frames={}
                for point,t,goal in path: frames[math.ceil(t)]=(point,goal)
                found=False
                for t,(point,goal) in frames.items():
                    if goal: break
                    test=nav.routes(point)
                    if nav.cost(me,test)<=t*a.speed+a.pr+a.br:
                        target=point; found=True; break
                if not found and path: target=path[-1][0]
        elif owner==enemy_id:
            target=(enemy[0],min(a.h-a.pr,max(a.pr,enemy[1]-sign*2)))
        route=nav.routes(target)
        def value(item):
            name,p=item; cost=nav.cost(p,route)
            if not math.isfinite(cost): cost=distance(p,target)+30
            return -cost+(.1 if name!='STAY' else 0)
        return {'move':max(moves,key=value)[0]}

    def attack(self,obs,me,enemy,moves,sign):
        a=self.arena; nav=self.nav; ball=obs['state']['ball']
        powers=obs['action_space']['kick']['power']; kicks=obs['action_space']['kick']['direction']
        goal_y=a.h-25 if sign>0 else 25
        targets=[(a.w/2+offset*a.gw,goal_y) for offset in (-.35,0,.35)]
        routes=[nav.routes(p) for p in targets if a.valid(p)]
        def carry_value(item):
            name,p=item
            cost=min((nav.cost(p,r) for r in routes),default=distance(p,(a.w/2,goal_y)))
            if not math.isfinite(cost): cost=distance(p,(a.w/2,goal_y))+30
            gap=distance(p,enemy)
            risk=max(0,14-gap) if ball['possession_steps']>=2 else max(0,8-gap)
            return -cost-self.settings['carry_risk']*risk+.03*sign*(p[1]-me[1])
        carry=max(moves,key=carry_value); best_score=-float('inf'); best=None
        trajectories={}
        for name,p in moves:
            for direction in kicks:
                if direction not in DIRECTIONS or direction=='STAY': continue
                dx,dy=DIRECTIONS[direction]
                origin=(p[0]+dx*(a.pr+a.br+.05),p[1]+dy*(a.pr+a.br+.05))
                path=a.trajectory(origin,(dx,dy),self.settings['kick_distances'][max(powers)-1])
                trajectories[(name,direction)]=path
                risk=0.; own_intercept=False
                for point,t,goal in path:
                    gap=distance(point,enemy)-(a.pr+a.br)
                    # All of the opponent's movement is applied before this
                    # frame's first ball substep. Fractional t underestimates
                    # interception reach, especially on close counterattacks.
                    reach=math.ceil(t)*a.speed
                    if gap<=0 or (t<=1 and gap<=a.speed+.15): risk=max(risk,2.)
                    risk=max(risk,max(0.,(reach-gap)/max(1.,reach)))
                    if t<=1 and distance(point,p)<=a.pr+a.br: own_intercept=True
                    if goal:
                        if goal==sign and not own_intercept:
                            score=100-self.settings['shot_risk']*risk-t*.5
                            if score>best_score:
                                best_score=score; best={'move':name,'kick':{'direction':direction,'power':max(powers)}}
                        break
        if best is not None and best_score>self.settings['shot_threshold']: return best
        if ball['possession_steps']>=8 or (ball['possession_steps']>=3 and distance(me,enemy)<10):
            escape=None; best_escape=-float('inf')
            for name,p in moves:
                for direction in kicks:
                    if direction not in DIRECTIONS or direction=='STAY': continue
                    dx,dy=DIRECTIONS[direction]
                    if sign*dy<0: continue
                    origin=(p[0]+dx*(a.pr+a.br+.05),p[1]+dy*(a.pr+a.br+.05))
                    for power in powers:
                        travel=self.settings['kick_distances'][power-1]
                        cached=trajectories[(name,direction)]
                        if abs(travel/a.bs-round(travel/a.bs))<1e-9:
                            path=[sample for sample in cached if sample[1]<=travel/a.bs]
                        else:
                            path=a.trajectory(origin,(dx,dy),travel)
                        if not path or path[-1][2]==-sign: continue
                        endpoint=path[-1][0]
                        if any(t<=1 and distance(q,p)<=a.pr+a.br for q,t,_ in path): continue
                        route=nav.routes(endpoint)
                        enemy_route=nav.cost(enemy,route); own_route=nav.cost(p,route)
                        if not math.isfinite(enemy_route): enemy_route=distance(enemy,endpoint)+20
                        if not math.isfinite(own_route): own_route=distance(p,endpoint)+20
                        score=enemy_route-own_route+.3*sign*(endpoint[1]-p[1])
                        pass_risk=max((max(0.,(math.ceil(t)*a.speed+a.pr+a.br-distance(q,enemy))/max(a.speed,math.ceil(t)*a.speed)) for q,t,_ in path),default=0.)
                        score-=self.settings.get('pass_risk',0.)*pass_risk
                        if any(t<=1 and distance(q,enemy)<a.pr+a.br+a.speed+.15 for q,t,_ in path): score-=80
                        if score>best_escape:
                            best_escape=score; escape={'move':name,'kick':{'direction':direction,'power':power}}
            if escape is not None: return escape
        return {'move':carry[0]}
