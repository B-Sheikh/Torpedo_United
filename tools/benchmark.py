"""Benchmark unchanged official physics and opponents, alternating both sides."""
import argparse
import json
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--kit',required=True,type=Path)
p.add_argument('--submission',type=Path,default=ROOT/'submission')
p.add_argument('--model',type=Path)
p.add_argument('--start-seed',type=int,default=11001)
p.add_argument('--seeds',type=int,default=10)
p.add_argument('--opponents',nargs='+',default=['organizer-rl','simple','aggressive','counter'])
p.add_argument('--output',type=Path,default=ROOT/'reports'/'benchmark.json')
args=p.parse_args()
sys.path.insert(0,str(args.kit.resolve())); sys.path.insert(0,str(args.submission.resolve()))
from soccer_env import GameConfig,SoccerEnv
from organizer_rl_bot.policy import OrganizerRLOpponent as Organizer
from soccer_env.bots import practice_action,aggressive_action,counter_action
from team_bot.policy import Policy
config=GameConfig.from_json(args.kit/'config'/'game.json')
rows=[]
for opponent_name in args.opponents:
 for seed in range(args.start_seed,args.start_seed+args.seeds):
  for side in ['player_1','player_2']:
   bot=Policy.load(args.model or args.submission/'team_bot'/'models'/'planner.json')
   org=Organizer(args.kit/'organizer_rl_bot'/'models'/'balanced_united_rl.json') if opponent_name=='organizer-rl' else None
   opponent=org.choose_action if org else {'simple':practice_action,'aggressive':aggressive_action,'counter':counter_action}[opponent_name]
   other='player_2' if side=='player_1' else 'player_1'
   env=SoccerEnv(config); obs=env.reset(seed=seed); elapsed=[]; events={}; illegal=0
   while not env.done:
    start=time.perf_counter(); action=bot.choose_action(obs[side]); elapsed.append(time.perf_counter()-start)
    legal=obs[side]['action_space']
    illegal+=int(action.get('move') not in legal['move'])
    if 'kick' in action:
     illegal+=int(action['kick'].get('direction') not in legal['kick']['direction'] or action['kick'].get('power') not in legal['kick']['power'])
    opposing=opponent(obs[other])
    obs,info=env.step(action,opposing) if side=='player_1' else env.step(opposing,action)
    for event in info['events']: events[event['type']]=events.get(event['type'],0)+1
   result=env.result(); gf=result['score'][side]; ga=result['score'][other]
   row={'opponent':opponent_name,'seed':seed,'side':side,'goals_for':gf,'goals_against':ga,'outcome':'win' if gf>ga else 'loss' if gf<ga else 'draw','iterations':env.iteration,'mean_decision_ms':1000*sum(elapsed)/len(elapsed),'p95_decision_ms':1000*sorted(elapsed)[min(len(elapsed)-1,int(.95*len(elapsed)))],'max_decision_ms':1000*max(elapsed),'illegal_actions':illegal,'events':events}
   rows.append(row); print(opponent_name,seed,side,gf,ga,'max_ms',round(row['max_decision_ms'],1),flush=True)
summary={}
for name in args.opponents:
 matches=[r for r in rows if r['opponent']==name]
 pairs={}
 for row in matches: pairs[row['seed']]=pairs.get(row['seed'],0)+row['goals_for']-row['goals_against']
 summary[name]={'matches':len(matches),'wins':sum(r['outcome']=='win' for r in matches),'draws':sum(r['outcome']=='draw' for r in matches),'losses':sum(r['outcome']=='loss' for r in matches),'goals_for':sum(r['goals_for'] for r in matches),'goals_against':sum(r['goals_against'] for r in matches),'max_decision_ms':max(r['max_decision_ms'] for r in matches),'illegal_actions':sum(r['illegal_actions'] for r in matches),'two_leg_series_wins':sum(d>0 for d in pairs.values()),'two_leg_series_draws':sum(d==0 for d in pairs.values()),'two_leg_series_losses':sum(d<0 for d in pairs.values())}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps({'config':config.__dict__,'summary':summary,'matches':rows},indent=2))
print(json.dumps(summary,indent=2))
