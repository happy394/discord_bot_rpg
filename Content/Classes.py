import discord
from discord import Game, Intents, ButtonStyle
from discord.ui import View, Button
from discord.ext import commands

from settings import *
import mysql.connector

import enum, random, sys
from copy import deepcopy


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

    def fight(self, other):
        defense = min(other.defense, 19)  # cap defense value
        chance_to_hit = random.randint(0, 20 - defense)
        if chance_to_hit:
            damage = self.attack
        else:
            damage = 0

        other.hp -= damage

        return self.attack, other.hp <= 0  # (damage, fatal)


# Helper functions
def str_to_class(classname):
    return getattr(sys.modules[__name__], classname)


class _Character(Actor):

    level_cap = 10

    def __init__(self, db, name, hp, max_hp, attack, defense, mana, level, xp, gold, inventory, mode, battling, user_id):
        super().__init__(name, hp, max_hp, attack, defense, xp, gold)
        self.db = db
        self.mana = mana
        self.level = level

        self.inventory = inventory

        self.mode = mode

        if battling is not None:
            enemy_class = str_to_class(battling["enemy"])
            self.battling = enemy_class()
            self.battling.rehydrate(**battling)
        else:
            self.battling = None

        self.user_id = user_id

    def save_to_db(self):
        character_dict = deepcopy(vars(self))
        if self.battling is not None:
            character_dict["battling"] = deepcopy(vars(self.battling))
        cursor = self.db.cursor(buffered=True)
        sql_formula = ("INSERT INTO characters_2 (name, hp, max_hp, attack, defense, mana, level, xp, gold, "
                       "inventory, mode, battling, user_id)"
                       "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
        cursor.execute(sql_formula, (self.name, self.hp, self.max_hp, self.attack, self.defense, self.mana, self.level, self.xp, self.gold, self.inventory, self.mode, self.battling, self.user_id))
        self.db.commit()

    def hunt(self):
        # Generate random enemy to fight
        while True:
            enemy_type = random.choice(Enemy.__subclasses__())

            if enemy_type.min_level <= self.level:
                break

        enemy = enemy_type()

        # Enter battle mode
        self.mode = GameMode.BATTLE
        self.battling = enemy

        # Save changes to DB after state change
        self.save_to_db()

        return enemy

    def fight(self, enemy):
        outcome = super().fight(enemy)

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

    def die(self, player_id):
        cursor = self.db.cursor(buffered=True)
        sql_get = f"DELETE FROM characters WHERE user_id = {self.user_id}"
        cursor.execute(sql_get)
        self.db.commit()
        return


class Enemy(Actor):

    def __init__(self, name, max_hp, attack, defense, xp, gold):
        super().__init__(name, max_hp, max_hp, attack, defense, xp, gold)
        self.enemy = self.__class__.__name__

    def rehydrate(self, name, hp, max_hp, attack, defense, xp, gold, enemy):
        self.name = name
        self.hp = hp
        self.max_hp = max_hp
        self.attack = attack
        self.defense = defense
        self.xp = xp
        self.gold = gold


class GiantRat(Enemy):
    min_level = 1

    def __init__(self):
        super().__init__("🐀 Giant Rat", 2, 1, 1, 1, 1)  # HP, attack, defense, XP, gold


class GiantSpider(Enemy):
    min_level = 1

    def __init__(self):
        super().__init__("🕷️ Giant Spider", 3, 2, 1, 1, 2)  # HP, attack, defense, XP, gold


class Bat(Enemy):
    min_level = 1

    def __init__(self):
        super().__init__("🦇 Bat", 4, 2, 1, 2, 1)  # HP, attack, defense, XP, gold


class Crocodile(Enemy):
    min_level = 2

    def __init__(self):
        super().__init__("🐊 Crocodile", 5, 3, 1, 2, 2)  # HP, attack, defense, XP, gold


class Wolf(Enemy):
    min_level = 2

    def __init__(self):
        super().__init__("🐺 Wolf", 6, 3, 2, 2, 2)  # HP, attack, defense, XP, gold


class Poodle(Enemy):
    min_level = 3

    def __init__(self):
        super().__init__("🐩 Poodle", 7, 4, 1, 3, 3)  # HP, attack, defense, XP, gold


class Snake(Enemy):
    min_level = 3

    def __init__(self):
        super().__init__("🐍 Snake", 8, 4, 2, 3, 3)  # HP, attack, defense, XP, gold


class Lion(Enemy):
    min_level = 4

    def __init__(self):
        super().__init__("🦁 Lion", 9, 5, 1, 4, 4)  # HP, attack, defense, XP, gold


class Dragon(Enemy):
    min_level = 5

    def __init__(self):
        super().__init__("🐉 Dragon", 10, 6, 2, 5, 5)  # HP, attack, defense, XP, gold


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
