import discord
from discord import Game, Intents, ButtonStyle
from discord.ui import View, Button
from discord.ext import commands
import psycopg2

from settings import *
import mysql.connector

import enum, random, sys, json


# connect to database
def connect_database():
    connection = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    print('[*] Connected to database: %s' % DB_NAME)
    return connection


db = connect_database()


# Helper functions
def str_to_class(classname):
    return getattr(sys.modules[__name__], classname["enemy"])


def _get_enemy_db(_id):
    cursor = db.cursor(buffered=True)
    sql_get = f"SELECT battling FROM characters WHERE user_id = {_id}"
    cursor.execute(sql_get)
    x = cursor.fetchall()[0][0]
    res = json.loads(x)
    return res


# Game modes
class GameMode(enum.IntEnum):
    ADVENTURE = 1
    BATTLE = 2


# Living creatures
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
        print(item, item.attack)
        defense = min(other.defense, 19)  # cap defense value
        chance_to_hit = random.randint(0, 20 - defense)
        if chance_to_hit >= 5:
            damage = self.attack
        else:
            damage = 0

        other.hp -= damage

        return damage, other.hp <= 0  # (damage, fatal)


class Character_(Actor):
    db = db
    level_cap = 10

    def __init__(self, name, hp, max_hp, attack, defense, xp, gold, inventory, mana, level, mode, battling, location,
                 user_id):
        super().__init__(name, hp, max_hp, attack, defense, xp, gold)
        self.inventory = inventory
        self.mana = mana
        self.level = level
        self.mode = mode

        if battling is not None:
            self.battling = battling
        else:
            self.battling = None

        self.location = location
        self.user_id = user_id

    def save_to_db(self):
        cursor = self.db.cursor(buffered=True)
        sql_formula = (f"UPDATE characters SET battling = %s, "
                       f"mode = %s,"
                       f"xp = %s,"
                       f"gold = %s,"
                       f"hp = %s,"
                       f"max_hp = %s,"
                       f"level = %s,"
                       f"attack = %s "
                       f"WHERE user_id = {self.user_id}")
        if self.battling:
        # sql_formula2 = ("INSERT INTO enemies_by_users (user_id, name, max_hp, attack, defense, xp, gold) "
        #                 "VALUES (%s, %s, %s, %s, %s, %s, %s)")
            cursor.execute(sql_formula, (json.dumps(self.battling.__dict__), self.mode, self.xp, self.gold, self.hp, self.max_hp, self.level, self.attack))
        else:
            cursor.execute(sql_formula, (self.battling, self.mode, self.xp, self.gold, self.hp, self.max_hp, self.level, self.attack))

        # cursor.execute(sql_formula2, [self.battling.user_id,
        #                               self.battling.name,
        #                               self.battling.max_hp,
        #                               self.battling.attack,
        #                               self.battling.defense,
        #                               self.battling.xp,
        #                               self.battling.gold])
        self.db.commit()
        return

    def hunt(self):
        # Generate random enemy to fight
        while True:
            enemy_type = random.choice(Enemy.__subclasses__())
            if enemy_type.min_level <= self.level:
                break

        # Enter battle mode
        self.mode = GameMode.BATTLE
        self.battling = enemy_type()

        # Save changes to DB after state change
        self.save_to_db()

        return enemy_type()

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
        cursor = self.db.cursor(buffered=True)
        sql_get = f"DELETE FROM characters WHERE user_id = {self.user_id}"
        cursor.execute(sql_get)
        self.db.commit()
        return


class Enemy(Actor):

    def __init__(self, name, hp, max_hp, attack, defense, xp, gold):
        super().__init__(name, hp, max_hp, attack, defense, xp, gold)
        self.enemy = self.__class__.__name__


class GiantRat(Enemy):
    min_level = 1

    def __init__(self):
        super().__init__("🐀 Giant Rat", 2, 2, 1, 1, 1, 1)  # HP, attack, defense, XP, gold


class GiantSpider(Enemy):
    min_level = 1

    def __init__(self):
        super().__init__("🕷️ Giant Spider", 3, 3, 2, 1, 1, 2)  # HP, attack, defense, XP, gold


class Bat(Enemy):
    min_level = 1

    def __init__(self):
        super().__init__("🦇 Bat", 4, 4, 2, 1, 2, 1)  # HP, attack, defense, XP, gold


class Crocodile(Enemy):
    min_level = 2

    def __init__(self):
        super().__init__("🐊 Crocodile", 5, 5, 3, 1, 2, 2)  # HP, attack, defense, XP, gold


class Wolf(Enemy):
    min_level = 2

    def __init__(self):
        super().__init__("🐺 Wolf", 6, 6, 3, 2, 2, 2)  # HP, attack, defense, XP, gold


class Poodle(Enemy):
    min_level = 3

    def __init__(self):
        super().__init__("🐩 Poodle", 7, 7, 4, 1, 3, 3)  # HP, attack, defense, XP, gold


class Snake(Enemy):
    min_level = 3

    def __init__(self):
        super().__init__("🐍 Snake", 8, 8, 4, 2, 3, 3)  # HP, attack, defense, XP, gold


class Lion(Enemy):
    min_level = 4

    def __init__(self):
        super().__init__("🦁 Lion", 9, 9, 5, 1, 4, 4)  # HP, attack, defense, XP, gold


class Dragon(Enemy):
    min_level = 5

    def __init__(self):
        super().__init__("🐉 Dragon", 10, 10, 6, 2, 5, 5)  # HP, attack, defense, XP, gold


# items
class Item:
    def __init__(self, name, min_level, attack, defense, mana, gold):
        self.name = name
        self.min_level = min_level
        self.attack = attack
        self.defense = defense
        self.mana = mana
        self.gold = gold


class Sword(Item):
    def __init__(self):
        super().__init__("Sword", 1, 2, 0, 0, 5)


class Character:
    def __init__(self, name, age, race, clas):
        self.name = name
        self.age = age
        self.race = race
        self.clas = clas
        self.attack = 5
        self.defence = 5
        self.inventory = {"sword": 5}

    def print_character(self):
        return (f"Your character: ```Name: {self.name}\nAge: {self.age}\n"
                f"Race: {self.race}\n"
                f"Class: {self.clas}\n```")


classes_list = ["Warrior", "Wizard", "Rogue", "Healer"]
races_list = ["Human", "Elf", "Dwarf", "Ork"]


class RaceView(View):
    answer = None
    options = []
    for i in races_list:
        options.append(discord.SelectOption(label=f"{i}", value=f"{i}"))

    @discord.ui.select(placeholder="Choose your race:", options=options)
    async def select_class(self, select: discord.ui.Select, interaction):
        self.answer = select
        select.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()


class ClassView(View):
    answer1 = None
    options = []
    for i in classes_list:
        options.append(discord.SelectOption(label=f"{i}", value=f"{i}"))

    @discord.ui.select(placeholder="Choose your class:", options=options)
    async def select_class(self, select: discord.ui.Select, interaction):
        self.answer1 = select
        select.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()
