"""Meaningful regression checks against the independently supplied engine."""
import copy
import json
import os
import random
import subprocess
import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
KIT=Path(os.environ.get('CONVCUP_KIT',str(ROOT.parent/'official'/'participants'))).resolve()
sys.path.insert(0,str(KIT)); sys.path.insert(0,str(ROOT/'submission'))
from soccer_env import GameConfig,SoccerEnv
from soccer_env.bots import practice_action
from team_bot.policy import Policy,DIRECTIONS

MODEL=ROOT/'submission'/'team_bot'/'models'/'planner.json'

class AgentTests(unittest.TestCase):
    def test_selects_real_first_frame_interception(self):
        config=GameConfig.from_json(KIT/'config'/'game.json')
        env=SoccerEnv(replace(config,obstacle_count=0)); env.reset(419)
        env.players={'player_1':(54.,85.),'player_2':(50.,35.)}
        env.possession=None; env.ball_position=(50.,72.)
        env.ball_velocity=(0.,8.); env.ball_remaining_distance=64.
        bot=Policy.load(MODEL)
        action=bot.choose_action(env.observations()['player_1'])
        env.step(action,{'move':'STAY'})
        self.assertEqual(env.possession,'player_1')

    def test_does_not_give_close_defender_an_immediate_interception(self):
        config=GameConfig.from_json(KIT/'config'/'game.json')
        env=SoccerEnv(config); env.reset(41001)
        env.players={'player_1':(52.82842712474619,67.48528137423858),'player_2':(50.,77.)}
        env.possession='player_2'; env.ball_position=env.players['player_2']; env.possession_steps=3
        bot=Policy.load(MODEL)
        action=bot.choose_action(env.observations()['player_2'])
        env.step({'move':'UP_LEFT'},action)
        self.assertNotEqual(env.possession,'player_1')

    def test_legal_deterministic_read_only_both_sides(self):
        config=GameConfig.from_json(KIT/'config'/'game.json')
        for side in ('player_1','player_2'):
            env=SoccerEnv(config); obs=env.reset(85013)
            one,two=Policy.load(MODEL),Policy.load(MODEL)
            for _ in range(60):
                before=copy.deepcopy(obs[side])
                action=one.choose_action(obs[side])
                self.assertEqual(action,two.choose_action(obs[side]))
                self.assertEqual(before,obs[side])
                self.assertIn(action['move'],obs[side]['action_space']['move'])
                if 'kick' in action:
                    self.assertEqual(obs[side]['state']['ball']['possession'],side)
                    self.assertIn(action['kick']['direction'],obs[side]['action_space']['kick']['direction'])
                    self.assertIn(action['kick']['power'],obs[side]['action_space']['kick']['power'])
                other='player_2' if side=='player_1' else 'player_1'
                opposite=practice_action(obs[other])
                obs,_=env.step(action,opposite) if side=='player_1' else env.step(opposite,action)
                if env.done: break

    def test_ball_forecast_matches_official_free_ball_physics(self):
        # Keep players away to isolate rebounds and range depletion. These are
        # development fixtures only; inference never accesses the engine.
        rng=random.Random(732)
        for seed in (912,913,914):
            env=SoccerEnv(GameConfig.from_json(KIT/'config'/'game.json'))
            obs=env.reset(seed); policy=Policy.load(MODEL)
            policy.choose_action(obs['player_1']); arena=policy.arena
            for direction in DIRECTIONS.values():
                if direction==(0.,0.): continue
                origin=(rng.uniform(15,85),rng.uniform(45,95))
                env.possession=None; env.players={'player_1':(-1000.,-1000.),'player_2':(1000.,1000.)}
                env.ball_position=origin; env.ball_velocity=(direction[0]*8,direction[1]*8); env.ball_remaining_distance=96
                path=arena.trajectory(origin,direction,96)
                frames={}
                for point,t,goal in path: frames[math_ceil(t)]=(point,goal)
                for _,(expected,goal) in frames.items():
                    scorer=env._move_ball()
                    self.assertAlmostEqual(expected[0],env.ball_position[0],places=7)
                    self.assertAlmostEqual(expected[1],env.ball_position[1],places=7)
                    if goal:
                        self.assertEqual(scorer,'player_1' if goal==1 else 'player_2'); break
                    self.assertIsNone(scorer)

    def test_protocol_multiple_matches_unknown_and_malformed_message(self):
        env=SoccerEnv(); observation=env.reset(401)['player_1']
        request='\n'.join([json.dumps({'type':'hello'}),'invalid-json',
            json.dumps({'type':'observation','observation':observation}),
            json.dumps({'type':'match_end'})])+'\n'
        proc=subprocess.run([sys.executable,'-m','team_bot.bot','--model','team_bot/models/planner.json'],
            input=request,capture_output=True,text=True,cwd=ROOT/'submission',timeout=5)
        self.assertEqual(proc.returncode,0)
        responses=[json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(len(responses),2)
        self.assertEqual(responses[0],{'move':'STAY'})
        self.assertIn(responses[1]['move'],DIRECTIONS)
        self.assertIn('bot error:',proc.stderr)

def math_ceil(value):
    import math
    return math.ceil(value)

if __name__=='__main__': unittest.main()
