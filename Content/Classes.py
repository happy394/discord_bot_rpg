import psycopg2
import discord
import enum
import random
import json

from settings import *
from discord import Intents, Game
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


db = connect_database()
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=Intents.all())
cursor = db.cursor()


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


class GameMode(enum.IntEnum):
    ADVENTURE = 1
    BATTLE = 2


def status_embed(ctx, character):
    mode_color = {
        GameMode.BATTLE: 0xDC143C,
        GameMode.ADVENTURE: 0x005EB8,
    }
    mode_text = ""
    # Current mode
    if character.mode == GameMode.BATTLE:
        mode_text = f"Currently battling a {character.battling.name}."
    elif character.mode == GameMode.ADVENTURE:
        mode_text = "Currently adventuring."

    # Create embed with description as current mode
    embed = discord.Embed(title=f"{character.name} status", description=mode_text, color=mode_color[character.mode])
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar)

    # Stats field
    _, xp_needed = character.ready_to_level_up()

    # **MANA:**  {character.mana}
    embed.add_field(name="Stats", value=f"""
        **HP:**    {character.hp}/{character.max_hp}
        **ATTACK:**   {character.attack}
        **DEFENSE:**   {character.defense}
        **LEVEL:** {character.level}
        **XP:**    {character.xp}/{character.xp + xp_needed}
            """, inline=True)

    embed.add_field(name="", value="")

    # Inventory field
    inventory_text = f"Gold: {character.gold}\n"
    inventory = character.inventory
    if inventory:
        inventory_text += "\n".join(inventory)

    embed.add_field(name="Inventory", value=inventory_text, inline=True)
    return embed


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


class Character(Actor):
    level_cap = 10

    def __init__(self, user_id, name, level, xp, hp, max_hp, gold, attack, defense, battling, location, mode,
                 inventory):
        super().__init__(name, hp, max_hp, attack, defense, xp, gold)
        self.user_id = user_id
        self.level = level
        self.battling = get_enemy_db(self.user_id) if battling else None
        self.location = location
        self.mode = mode
        self.inventory = inventory

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
                       f"attack = %s "
                       f"WHERE user_id = {self.user_id}")

        if self.battling:
            cursor.execute(sql_formula, (json.dumps(self.battling.__dict__), self.mode, self.xp, self.gold, self.hp,
                                         self.max_hp, self.level, self.attack))
        else:
            cursor.execute(sql_formula, (None, self.mode, self.xp, self.gold, self.hp, self.max_hp, self.level,
                                         self.attack))

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


class Item:
    def __init__(self, name, gold, description, weight, additional):
        self.name = name
        self.gold = gold
        self.description = description
        self.weight = weight
        self.additional = additional


def create_character_db(character: Character) -> None:
    sql = ('INSERT INTO character '
           '(user_id, name, level, xp, hp, max_hp, gold, attack, defense, battling, location, mode) '
           'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)')
    sql2 = ('INSERT INTO characters_inventories'
            '(user_id, title, amount)'
            'VALUES (%s, %s, %s)')

    cursor.execute(sql, (character.user_id, character.name, character.level, character.xp,
                         character.hp, character.max_hp, character.gold,
                         character.attack, character.defense, character.battling,
                         character.location, character.mode))

    if character.inventory:
        for i in character.inventory:
            cursor.execute(sql2, (character.user_id, i.name, 1))

    db.commit()


def get_character_db(_id) -> Character or None:
    sql_character = f'SELECT * FROM character WHERE user_id = {_id}'
    sql_inventory = f'SELECT title FROM characters_inventories WHERE user_id = {_id}'

    cursor.execute(sql_character)
    res = cursor.fetchall()
    cursor.execute(sql_inventory)
    res += cursor.fetchall()

    if not res:
        return None

    character = Character(*res[0], inventory=[])
    for i in res[1:]:
        character.inventory.append(*i)

    return character


class Rpg(commands.Cog):

    @commands.Cog.listener()
    async def on_ready(self):
        await bot.change_presence(activity=Game(name="long swords"))
        print("[*] Connected to discord as: %s" % bot.user.name)

    @commands.command(name="create", help="Create a character")
    async def _create(self, ctx, name=None):
        if ctx.channel.id == 1224681797179281458 or ctx.channel.id == 878623706908352565:
            user = ctx.message.author

            # if no name is specified, use the creator's nickname
            if not name:
                name = user.name

            if not get_character_db(user.id):
                role = discord.Role
                role.id = 1224683255744168040

                character = Character(
                    user_id=user.id,
                    name=name,
                    level=1,
                    xp=0,
                    hp=10,
                    max_hp=10,
                    gold=5,
                    attack=2,
                    defense=5,
                    battling=None,
                    location="forest",
                    mode=GameMode.ADVENTURE,
                    inventory=["Wooden sword", "Shield"]
                )

                try:
                    create_character_db(character)
                except Exception:
                    await ctx.reply(content="Sorry! Something went wrong.")
                    raise Exception("Couldn't save character to a database")

                await user.add_roles(role)
                await ctx.reply(content=f"Your character has been created successfully!\nYou are now located in the "
                                        f"forest.\nCheck the **{BOT_PREFIX}status** command.")

            else:
                await ctx.reply(f"You already have a character! Check the **{BOT_PREFIX}status** command.")

        else:
            await ctx.reply(content="This command should be used in `character-creation` channel.")

    @commands.command(name="status", help="Get information about your character")
    async def _status(self, ctx):
        character = get_character_db(ctx.message.author.id)

        if not character:
            await ctx.reply(content=f"You don't have a character! Check the **{BOT_PREFIX}create** command")
        else:
            embed = status_embed(ctx, character)
            await ctx.message.reply(embed=embed)

    @commands.command(name="explore", help="Search for enemies in your location")
    async def _explore(self, ctx):
        await ctx.message.reply(content="Sorry! This command is currently under development.")

    @commands.command(name="hunt", help="Look for an enemy to fight.")
    async def _hunt(self, ctx):
        if ctx.channel.id in [1224681797179281458, 1224683073212518591]:
            await ctx.reply("You can't hunt in this channel.")
        else:
            character = get_character_db(ctx.message.author.id)

            if character.mode != GameMode.ADVENTURE:
                await ctx.message.reply("Can only call this command outside of battle!")
                return

            enemy = character.hunt()

            await ctx.message.reply(f"You encounter a {enemy.name}. "
                                    f"Do you `.fight` or `.flee`?."
                                    f"\n`.flee` command will work in several days!")

    @commands.command(name="fight", help="Fight the current enemy.")
    async def fight(self, ctx, *, item_given=None):
        user = ctx.message.author
        character = get_character_db(user.id)
        if character.mode != GameMode.BATTLE:
            await ctx.message.reply("Can only call this command in battle!")
            return

        # Simulate battle
        item = get_item_db(item_given)
        if item == 0:
            await ctx.message.reply("You don't have this item or typed its name wrong. Please try again!")
            return

        enemy = character.battling

        # Character attacks
        damage, killed = character.fight(enemy, item)
        if damage != 0:
            await ctx.message.reply(f"{character.name} attacks {enemy.name}, dealing {damage} damage!")
        else:
            await ctx.message.reply(f"{character.name} swings at {enemy.name}, but misses!")

        # End battle in victory if enemy killed
        if killed:
            xp, gold, ready_to_level_up = character.defeat(enemy)

            await ctx.message.reply(
                f"{character.name} vanquished the {enemy.name}, earning {xp} XP and {gold} GOLD. "
                f"HP: {character.hp}/{character.max_hp}.")

            if ready_to_level_up:
                await ctx.message.reply(
                    f"{character.name} has earned enough XP to advance to level {character.level + 1}. "
                    f"Enter `{BOT_PREFIX}levelup` with the stat (HP, ATTACK, DEFENSE) you would like to increase. e.g. "
                    f"`{BOT_PREFIX}levelup hp` or `{BOT_PREFIX}levelup attack`.")

            return

        # Enemy attacks
        damage, killed = enemy.fight(character, None)
        if damage != 0:
            await ctx.message.reply(f"{enemy.name} attacks {character.name}, dealing {damage} damage!")
        else:
            await ctx.message.reply(f"{enemy.name} tries to attack {character.name}, but misses!")

        character.battling = enemy
        character.save_to_db()  # enemy.fight() does not save automatically

        # End battle in death if character killed
        if killed:
            character.die()

            await ctx.message.reply(
                f"{character.name} was defeated by a {enemy.name} and is no more. Rest in peace, brave adventurer.")
            return

        # No deaths, battle continues
        await ctx.message.reply(f"The battle rages on! Do you `.fight` or `.flee`?")

    @commands.command(name="flee", help="Flee the current enemy.")
    async def flee(self, ctx):
        character = get_character_db(ctx.message.author.id)

        if character.mode != GameMode.BATTLE:
            await ctx.message.reply("Can only call this command in battle!")
            return

        enemy = character.battling
        damage, killed = character.flee(enemy)

        if killed:
            character.die()
            await ctx.message.reply(
                f"{character.name} was killed fleeing the {enemy.name}, and is no more. "
                f"Rest in peace, brave adventurer.")
        elif damage:
            await ctx.message.reply(
                f"{character.name} flees the {enemy.name}, taking {damage} damage. "
                f"HP: {character.hp}/{character.max_hp}")
        else:
            await ctx.message.reply(
                f"{character.name} flees the {enemy.name} with their life but not their dignity intact. "
                f"HP: {character.hp}/{character.max_hp}")

    @commands.command(name="levelup", help="Level up your character.")
    # implement buttons to choose which characteristics to upgrade or make an additional command for that
    async def _level_up(self, ctx, increase):
        character = get_character_db(ctx.message.author.id)
        if character:
            if character.mode != GameMode.ADVENTURE:
                await ctx.message.reply("Can only call this command outside of battle!")
                return

            ready, xp_needed = character.level_up(increase)
            if not ready:
                await ctx.message.reply(f"You need another {xp_needed} xp to advance to level {character.level + 1}")
                return

            if not increase:
                await ctx.message.reply("Please specify a stat to increase (hp, attack, defense)")
                return

            await ctx.message.reply("You have successfully advanced your character!")
        else:
            await ctx.reply(content=f"You don't have a character! Check the **{BOT_PREFIX}create** command")

    @commands.command(name="die", help="Destroy current character.")
    async def die(self, ctx):
        character = get_character_db(ctx.message.author.id)

        character.die()

        await ctx.message.reply(f"Character {character.name} is no more. Create a new one with `{BOT_PREFIX}create`.")

    # @commands.command(name="reset", help="[DEV] Destroy and recreate current character.")
    # async def reset(self, ctx):
    #     user_id = str(ctx.message.author.id)
    #
    #     # if user_id in db["characters"].keys():
    #     #     del db["characters"][user_id]
    #
    #     await ctx.message.reply(f"Character deleted.")
    #     await create(ctx)
