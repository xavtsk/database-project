"""Actual MariaDB/MongoDB integration tests; opt in with RUN_DB_TESTS=1.

Creates uniquely named disposable databases and drops only those databases.
Uses SQL_USER credentials from the environment; requires CREATE/DROP permission.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import os
import random
import unittest
import uuid

import pymysql

from backend.app import create_app
from backend.catalog import catalog
from backend.config import sql_options
from backend.db import transaction, query
from backend.battles.service import select_reward, generate_opponent, deliver_reward
from scripts.setup_databases import setup


@unittest.skipUnless(os.getenv('RUN_DB_TESTS')=='1','Set RUN_DB_TESTS=1 for real database checks')
class DatabaseIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous={k:os.environ.get(k) for k in ('SQL_DATABASE','MONGO_DATABASE')}
        cls.database='pokedex_test_'+uuid.uuid4().hex
        os.environ['SQL_DATABASE']=cls.database;os.environ['MONGO_DATABASE']=cls.database
        setup();catalog.cache_clear()
        cls.app=create_app({'TESTING':True})
        cls.logs=cls.app.extensions['battles']

    @classmethod
    def tearDownClass(cls):
        cls.app.extensions['mongo'].drop_database(cls.database)
        cls.app.extensions['mongo'].close()
        with pymysql.connect(**sql_options(database=False)) as connection:
            with connection.cursor() as cursor:cursor.execute(f'DROP DATABASE `{cls.database}`')
        for key,value in cls.previous.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value
        catalog.cache_clear()

    def setUp(self):
        self.client=self.app.test_client()
        token=self.client.get('/api/session').json['csrf']
        self.headers={'X-CSRF-Token':token}
        self.trainer=self.post('/api/profiles',{'name':'Integration trainer'}).json['trainer']['id']
        self.team=self.post('/api/starter',{'pokemon_id':7}).json['team_id']

    def post(self,url,data):return self.client.post(url,json=data,headers=self.headers)
    def start(self,difficulty='easy'):
        result=self.post('/api/battles',{'team_id':self.team,'difficulty':difficulty})
        self.assertEqual(result.status_code,201,result.json)
        return result.json

    def test_pokedex_filters_detail_csrf_and_starter_uniqueness(self):
        self.assertEqual(len(self.client.get('/api/pokemon').json['pokemon']),151)
        found=self.client.get('/api/pokemon?q=bulba&type=grass').json['pokemon']
        self.assertEqual([p['id'] for p in found],[1])
        self.assertGreaterEqual(len(self.client.get('/api/pokemon/132').json['moves']),4)
        self.assertEqual(self.client.post('/api/teams',json={}).status_code,403)
        self.assertEqual(self.post('/api/starter',{'pokemon_id':1}).status_code,400)
        self.assertEqual(len(self.client.get('/api/collection').json['pokemon']),1)

    def test_team_crud_constraints_and_analysis(self):
        member=self.client.get(f'/api/teams/{self.team}').json['members'][0]
        valid={'owned_id':member['owned_id'],'moves':member['moves']}
        for members in ([valid]*7,[valid,valid],[dict(valid,moves=[valid['moves'][0]]*4)],[dict(valid,owned_id=999999)],[dict(valid,moves=[999999,1,2,3])]):
            self.assertEqual(self.post('/api/teams',{'name':'Invalid','members':members}).status_code,400)
        created=self.post('/api/teams',{'name':'Second team','members':[valid]})
        self.assertEqual(created.status_code,201)
        team_id=created.json['id']
        self.assertEqual(self.client.put(f'/api/teams/{team_id}',json={'name':'Renamed','members':[valid]},headers=self.headers).status_code,200)
        report=self.client.get(f'/api/teams/{team_id}/analysis').json
        self.assertEqual(report['stats']['total_hp'],44)
        self.assertEqual(len(report['matchups']),18)
        self.assertEqual(self.client.delete(f'/api/teams/{team_id}',headers=self.headers).status_code,200)
        self.assertEqual(self.client.get(f'/api/teams/{team_id}').status_code,400)
        self.post('/api/profiles',{'name':'Another trainer'})
        self.assertEqual(self.client.get(f'/api/teams/{self.team}').status_code,400)
        self.assertEqual(self.post('/api/teams',{'name':'Stolen','members':[valid]}).status_code,400)

    def test_all_team_sizes_difficulties_and_move_eligibility(self):
        for size in range(1,7):
            player=list(catalog()[0].values())[:size]
            for difficulty in ('easy','medium','hard'):
                opponent,info=generate_opponent(player,difficulty,random.Random(40))
                self.assertEqual(len(opponent),size)
                self.assertEqual(len({p['id'] for p in opponent}),size)
                self.assertEqual(info['candidates'],100)
                self.assertTrue(all(len(p['moves'])>=4 for p in opponent))

    def test_action_revision_active_limit_and_resume(self):
        b=self.start()
        self.assertEqual(self.post('/api/battles',{'team_id':self.team,'difficulty':'medium'}).status_code,400)
        move=b['player']['members'][0]['moves'][0]['id']
        data={'revision':0,'action':{'kind':'move','move_id':move}}
        result=self.post(f'/api/battles/{b["_id"]}/actions',data)
        self.assertEqual(result.status_code,200,result.json)
        self.assertEqual(self.post(f'/api/battles/{b["_id"]}/actions',data).status_code,400)
        resumed=self.client.get(f'/api/battles/{b["_id"]}').json
        self.assertEqual(resumed['revision'],1)
        self.assertEqual(len(resumed['turns']),1)

    def test_reward_retry_after_partial_delivery_and_snapshot_history(self):
        b=self.start();stored=self.logs.find_one({'_id':b['_id']})
        stored.update(status='win',reward=select_reward(random.Random(2)),ended_at=datetime.now(timezone.utc),elapsed_seconds=2)
        self.logs.replace_one({'_id':b['_id']},stored)
        self.client.get(f'/api/battles/{b["_id"]}')
        count=len(self.client.get('/api/collection').json['pokemon'])
        self.logs.update_one({'_id':b['_id']},{'$set':{'reward.delivered':False}})
        self.client.get(f'/api/battles/{b["_id"]}')
        self.assertEqual(len(self.client.get('/api/collection').json['pokemon']),count)
        self.assertEqual(len(query('SELECT * FROM battle_rewards WHERE battle_id=%s',(b['_id'],))),1)
        self.client.delete(f'/api/teams/{self.team}',headers=self.headers)
        self.assertEqual(self.client.get(f'/api/battles/{b["_id"]}').json['initial']['player'],b['initial']['player'])

    def test_analytics_known_fixtures_and_species_deduplication(self):
        b=self.start();original=self.logs.find_one({'_id':b['_id']})
        self.logs.delete_one({'_id':b['_id']})
        for i,status in enumerate(('win','loss','draw')):
            row=deepcopy(original);row['_id']=str(uuid.uuid4());row.update(status=status,turn_count=i+1,elapsed_seconds=(i+1)*10)
            row['initial']['player']['members']*=2
            row['turns']=[{'number':1,'events':[{'kind':'move','side':'player','move_id':33,'move':'tackle'}]}]
            self.logs.insert_one(row)
        result=self.client.get('/api/analytics').json
        self.assertEqual(result['summary']['battles'],3)
        self.assertEqual(result['summary']['wins'],1)
        self.assertEqual(result['summary']['average_turns'],2)
        self.assertEqual(result['summary']['average_seconds'],20)
        self.assertEqual(result['pokemon'][0]['appearances'],3)
        self.assertEqual(result['moves'][0]['uses'],3)

    def test_rarity_boundaries_and_six_member_team(self):
        class FixedRandom:
            def __init__(self,roll):self.roll=roll
            def random(self):return self.roll
            def choice(self,pool):return pool[0]
        for value,rarity in ((0,'common'),(.599,'common'),(.60,'uncommon'),(.85,'rare'),(.97,'legendary'),(.999,'legendary')):
            self.assertEqual(select_reward(FixedRandom(value))['rarity'],rarity)
        with transaction() as cursor:
            for pokemon_id in (1,4,25,132,150):cursor.execute("INSERT INTO owned_pokemon(trainer_id,pokemon_id,source) VALUES (%s,%s,'reward')",(self.trainer,pokemon_id))
        owned=self.client.get('/api/collection').json['pokemon']
        members=[{'owned_id':o['owned_id'],'moves':[m['id'] for m in o['pokemon']['moves'][:4]]} for o in owned]
        created=self.post('/api/teams',{'name':'Full six','members':members})
        self.assertEqual(created.status_code,201)
        self.team=created.json['id'];b=self.start('hard')
        self.assertEqual(len(b['player']['members']),6)
        self.assertEqual(len(b['opponent']['members']),6)
