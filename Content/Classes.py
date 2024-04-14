import psycopg2
import enum
import random
import json

from settings import *
from discord import Intents
from discord.ext import commands


def connect_database():
    connection = psycopg2.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    print('[*] Connected to database: %s' % DB_NAME)
    return connection


# global variables
db = connect_database()
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=Intents.all())
cursor = db.cursor()


# functions
def get_enemy_db(_id):
    sql_get_enemy = f"SELECT battling FROM character WHERE user_id = {_id}"
    cursor.execute(sql_get_enemy)
    buff = cursor.fetchone()[0]
    enemy = Enemy(buff["level_req"], buff["name"], buff["hp"], buff["max_hp"], buff["attack"], buff["defense"],
                  buff["xp"], buff["gold"], buff["location"])
    return enemy


def get_items_db(character_class):
    res = []
    sql_item = (f"SELECT name, gold, description, weight, additional FROM item "
                f"WHERE name IN({str(character_class.inventory).replace("[", "").replace("]", "")})")

    cursor.execute(sql_item)
    for i in cursor.fetchall():
        buff = []
        for j in range(4):
            buff.append(i[j])
        buff.append(i[4])
        item = Item(*buff)
        res.append(item)

    return res


def get_item_db(item_name):
    if not item_name:
        return None
    sql_item = f"SELECT name, gold, description, weight, additional FROM item WHERE name = '{item_name}'"
    cursor.execute(sql_item)
    fetching = cursor.fetchone()
    if not fetching:
        return 0
    return Item(*fetching)


# classes
class GameMode(enum.IntEnum):
    ADVENTURE = 1
    BATTLE = 2


class Actor:

    def __init__(self, name, hp, max_hp, attack, defense, xp, gold):
        self.name = name
        self.hp = hp
        self.max_hp = max_hp
        self.attack = attack
        self.defense = defense
        self.xp = xp
        self.gold = gold

    def fight(self, other, item):
        defense = min(other.defense, 19)  # cap defense value
        chance_to_hit = random.randint(0, 20 - defense)
        if chance_to_hit >= 5:
            damage = (self.attack + item.additional["attack"]) if item else self.attack
        else:
            damage = 0

        other.hp -= damage

        return damage, other.hp <= 0  # (damage, fatal)


class Item:
    def __init__(self, name, gold, description, weight, additional):
        self.name = name
        self.gold = gold
        self.description = description
        self.weight = weight
        self.additional = additional


class Character(Actor):
    level_cap = 10

    def __init__(self, user_id, name, level, xp, hp, max_hp, gold, attack, defense, battling, location, mode, thread,
                 inventory):
        super().__init__(name, hp, max_hp, attack, defense, xp, gold)
        self.user_id = user_id
        self.level = level
        self.battling = get_enemy_db(self.user_id) if battling else None
        self.location = location
        self.mode = mode
        self.inventory = inventory
        self.thread = thread

        # remake list into list of classes
        if self.inventory:
            self.inventory = get_items_db(self)

    def save_to_db(self):
        sql_formula = (f"UPDATE character SET battling = %s, "
                       f"mode = %s,"
                       f"xp = %s,"
                       f"gold = %s,"
                       f"hp = %s,"
                       f"max_hp = %s,"
                       f"level = %s,"
                       f"attack = %s, "
                       f"thread = %s "
                       f"WHERE user_id = {self.user_id}")

        if self.battling:
            cursor.execute(sql_formula, (json.dumps(self.battling.__dict__), self.mode, self.xp, self.gold, self.hp,
                                         self.max_hp, self.level, self.attack, self.thread))
        else:
            cursor.execute(sql_formula, (None, self.mode, self.xp, self.gold, self.hp, self.max_hp, self.level,
                                         self.attack, self.thread))

        db.commit()
        return

    def hunt(self):
        while True:
            cursor.execute('SELECT level_req, name, hp, max_hp, attack, defense, xp, gold, location FROM enemy')
            enemy = Enemy(*random.choice(cursor.fetchall()))
            if enemy.level_req <= self.level:
                break

        # Enter battle mode
        self.mode = GameMode.BATTLE
        self.battling = enemy

        # Save changes to DB after state change
        self.save_to_db()

        return enemy

    def fight(self, enemy, item):
        outcome = super().fight(enemy, item)

        # Save changes to DB after state change
        self.save_to_db()

        return outcome

    def flee(self, enemy):
        if random.randint(0, 1 + self.defense):  # flee unscathed
            damage = 0
        else:  # take damage
            damage = enemy.attack / 2
            self.hp -= damage

        # Exit battle mode
        self.battling = None
        self.mode = GameMode.ADVENTURE

        # Save to DB after state change
        self.save_to_db()

        return damage, self.hp <= 0  # (damage, killed)

    def ready_to_level_up(self):
        if self.level == self.level_cap:  # zero values if we've ready the level cap
            return False, 0

        xp_needed = self.level * 10
        return self.xp >= xp_needed, xp_needed - self.xp  # (ready, XP needed)

    def level_up(self, increase):
        ready, _ = self.ready_to_level_up()
        if not ready:
            return False, self.level  # (not leveled up, current level)

        self.level += 1  # increase level
        setattr(self, increase, getattr(self, increase) + 1)  # increase chosen stat

        self.hp = self.max_hp  # refill HP

        # Save to DB after state change
        self.save_to_db()

        return True, self.level  # (leveled up, new level)

    def defeat(self, enemy):
        if self.level < self.level_cap:  # no more XP after hitting level cap
            self.xp += enemy.xp

        self.gold += enemy.gold  # loot enemy

        # Exit battle mode
        self.battling = None
        self.mode = GameMode.ADVENTURE

        # Check if ready to level up after earning XP
        ready, _ = self.ready_to_level_up()

        # Save to DB after state change
        self.save_to_db()

        return enemy.xp, enemy.gold, ready

    def die(self):
        cursor.execute(f"DELETE FROM characters_inventories WHERE user_id = {self.user_id}")
        cursor.execute(f"DELETE FROM character WHERE user_id = {self.user_id}")
        db.commit()
        return


class Enemy(Actor):

    def __init__(self, level_req, name, hp, max_hp, attack, defense, xp, gold, location):
        super().__init__(name, hp, max_hp, attack, defense, xp, gold)
        self.level_req = level_req
        self.location = location


class Shop:
    def __init__(self, goods):
        self.goods = goods
