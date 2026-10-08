"""Compare old/new policy calls on identical deterministic observation fixtures."""
import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(); p.add_argument('--kit',required=True,type=Path)
args=p.parse_args(); sys.path[:0]=[str(args.kit.resolve()),str(ROOT/'submission')]
from soccer_env import GameConfig,SoccerEnv
from soccer_env.bots import practice_action
from team_bot.policy import Policy
spec=importlib.util.spec_from_file_location('v1_policy',ROOT/'baselines/v1/team_bot/policy.py')
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
config=GameConfig.from_json(args.kit/'config/game.json')
corpus=[]
for seed in (91011,91012,91013):
    env=SoccerEnv(config); observations=env.reset(seed)
    for i in range(100):
        if i%3==0:
            for side in ('player_1','player_2'): corpus.append(observations[side])
        observations,_=env.step(practice_action(observations['player_1']),practice_action(observations['player_2']))
        if env.done: break
old=module.Policy.load(ROOT/'baselines/v1/team_bot/models/planner.json')
new=Policy.load(ROOT/'submission/team_bot/models/planner.json')
samples={'v1':[],'v2':[]}
for i,obs in enumerate(corpus):
    order=[('v1',old),('v2',new)]
    if i%2: order.reverse()
    for name,bot in order:
        start=time.perf_counter(); bot.choose_action(obs); samples[name].append((time.perf_counter()-start)*1000)
summary={}
for name,values in samples.items():
    ordered=sorted(values)
    summary[name]={'observations':len(values),'mean_ms':sum(values)/len(values),'median_ms':ordered[len(values)//2],'p95_ms':ordered[min(len(values)-1,int(.95*len(values)))],'max_ms':max(values)}
summary['mean_speedup']=summary['v1']['mean_ms']/summary['v2']['mean_ms']
summary['note']='Same observations, alternating call order on one machine. Run without other heavy workloads for useful timing comparisons; timings are not universal runtime guarantees.'
(ROOT/'reports/latency_comparison.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
