"""Independent condition tests; altered-physics results are not official rankings."""
import argparse
import copy
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--kit',required=True,type=Path)
p.add_argument('--seeds',type=int,default=2)
p.add_argument('--output',type=Path,default=ROOT/'reports'/'conditions.json')
args=p.parse_args()
sys.path[:0]=[str(args.kit.resolve()),str(ROOT/'submission')]
from soccer_env import GameConfig,SoccerEnv
from soccer_env.bots import counter_action,aggressive_action
from team_bot.policy import Policy
config=GameConfig.from_json(args.kit/'config'/'game.json')
model=ROOT/'submission'/'team_bot'/'models'/'planner.json'
conditions={
    'official':{},
    'alternate_kickoff':{'initial_possessor':'player_2'},
    'open_field':{'obstacle_count':0},
    'eight_obstacles':{'obstacle_count':8,'obstacle_width':9.,'obstacle_height':7.},
    'narrow_goal':{'goal_width':20.},
    'slower_players':{'player_speed':3.},
    'faster_players':{'player_speed':5.},
    'extended_match':{'maximum_iterations':800,'maximum_goals':15},
    'unannounced_ball_physics':{'ball_speed':10.,'kick_distances':(40.,80.,120.)},
}
rows=[]
for condition,changes in conditions.items():
    for seed in range(83001,83001+args.seeds):
        for side in ('player_1','player_2'):
            env=SoccerEnv(replace(config,**changes)); obs=env.reset(seed)
            agent=Policy.load(model); timings=[]; errors=0; drops=0
            other='player_2' if side=='player_1' else 'player_1'
            opponent=counter_action if seed%2 else aggressive_action
            while not env.done:
                before=copy.deepcopy(obs[side]); t=time.perf_counter()
                action=agent.choose_action(obs[side]); timings.append(time.perf_counter()-t)
                if before!=obs[side]: raise AssertionError('Observation mutated')
                legal=obs[side]['action_space']
                errors+=int(action.get('move') not in legal['move'])
                if 'kick' in action:
                    errors+=int(action['kick'].get('direction') not in legal['kick']['direction'] or action['kick'].get('power') not in legal['kick']['power'])
                opposite=opponent(obs[other])
                obs,info=env.step(action,opposite) if side=='player_1' else env.step(opposite,action)
                drops+=sum(e['type']=='drop_ball' for e in info['events'])
            gf,ga=env.score[side],env.score[other]
            rows.append({'condition':condition,'changes':changes,'seed':seed,'side':side,'opponent':'counter' if seed%2 else 'aggressive','goals_for':gf,'goals_against':ga,'iterations':env.iteration,'illegal_actions':errors,'drop_balls':drops,'max_decision_ms':1000*max(timings)})
            print(condition,seed,side,gf,ga,'errors',errors,flush=True)

# Goal-late game state probes, close contact, moving/loose ball and obstacle-edge
# possession. Synthetic fixtures deliberately inspect legal protocol behavior.
fixtures=[]
for side in ('player_1','player_2'):
    for name in ('ahead_late','behind_late','tied_late','contact','loose_ball','moving_ball','obstacle_edge'):
        env=SoccerEnv(config); env.reset(88009)
        other='player_2' if side=='player_1' else 'player_1'
        env.possession=side; env.ball_position=env.players[side]
        if name.endswith('_late'):
            env.iteration=390
            if name=='ahead_late': env.score[side]=6
            elif name=='behind_late': env.score[other]=6
        elif name=='contact':
            env.players={'player_1':(50.,70.),'player_2':(56.,70.)}
            env.ball_position=env.players[side]; env.possession_steps=3
        elif name=='loose_ball':
            env.possession=None; env.ball_position=(50.,70.); env.loose_ball_steps=19
        elif name=='moving_ball':
            env.possession=None; env.ball_position=(50.,70.); env.ball_velocity=(0.,8.); env.ball_remaining_distance=64.
        else:
            obstacle=env.obstacles[0]
            point=(obstacle.x-config.player_radius-.1,obstacle.y+obstacle.height/2)
            if env._valid_player_position(point): env.players[side]=point
            env.ball_position=env.players[side]; env.possession_steps=8
        bot=Policy.load(model); errors=0; steps=0; max_ms=0
        while not env.done and steps<40:
            observation=env.observations(); before=copy.deepcopy(observation[side]); start=time.perf_counter()
            action=bot.choose_action(observation[side]); max_ms=max(max_ms,(time.perf_counter()-start)*1000)
            if before!=observation[side]: raise AssertionError('Fixture observation mutated')
            legal=observation[side]['action_space']; errors+=int(action.get('move') not in legal['move'])
            if 'kick' in action: errors+=int(action['kick']['direction'] not in legal['kick']['direction'] or action['kick']['power'] not in legal['kick']['power'])
            opposite=counter_action(observation[other])
            env.step(action,opposite) if side=='player_1' else env.step(opposite,action)
            steps+=1
        fixtures.append({'scenario':name,'side':side,'iterations_exercised':steps,'illegal_actions':errors,'max_decision_ms':max_ms,'score':env.score})
summaries={}
for condition in conditions:
    sample=[r for r in rows if r['condition']==condition]
    summaries[condition]={'matches':len(sample),'wins':sum(r['goals_for']>r['goals_against'] for r in sample),'draws':sum(r['goals_for']==r['goals_against'] for r in sample),'losses':sum(r['goals_for']<r['goals_against'] for r in sample),'illegal_actions':sum(r['illegal_actions'] for r in sample),'max_decision_ms':max(r['max_decision_ms'] for r in sample),'drop_balls':sum(r['drop_balls'] for r in sample)}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps({'note':'Only official uses unchanged competition settings. Other cases are stress tests, not competition performance. Unannounced ball physics deliberately leaves inference assumptions unchanged. Fixtures verify protocol behavior, not guaranteed tactical success.','summary':summaries,'matches':rows,'fixtures':fixtures},indent=2))
print(json.dumps(summaries,indent=2))
if any(r['illegal_actions'] for r in rows+fixtures): raise SystemExit(1)
