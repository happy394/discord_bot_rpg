import discord
from Content.Classes import *


# functions
def status_embed(ctx, character) -> discord.Embed:
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


# bot commands
class Rpg(commands.Cog):

    @commands.Cog.listener()
    async def on_ready(self):
        await bot.change_presence(activity=discord.Game(name="long swords"))
        print("[*] Connected to discord as: %s" % bot.user.name)

    @commands.command(name="create", help="Create a character")
    async def _create(self, ctx, name=None):
        if ctx.channel.id == 1224681797179281458 or ctx.channel.id == 878623706908352565:
            user = ctx.message.author

            # if no name is specified, use the creator's nickname
            if not name:
                name = user.name

            if get_character_db(user.id):
                await ctx.reply(f"You already have a character! Check the **{BOT_PREFIX}status** command.")
            else:
                role = discord.Role
                role.id = 1224683255744168040

                base_character = Character(
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
                    inventory=["Wooden sword", "Shield"],
                    thread=None
                )

                try:
                    create_character_db(base_character)
                except Exception:
                    await ctx.reply(content="Sorry! Something went wrong.")
                    raise Exception("Couldn't save character to a database")

                await user.add_roles(role)
                await ctx.reply(content=f"Your character has been created successfully!\nYou are now located in the "
                                        f"forest.\nCheck the **{BOT_PREFIX}status** and **{BOT_PREFIX}hunt** "
                                        f"commands.")

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
        character = get_character_db(ctx.message.author.id)
        thread = character.thread

        if ctx.channel.id in [1224681797179281458, 1224683073212518591, thread]:
            await ctx.reply("You can't hunt in this channel.")
        else:

            if character.mode != GameMode.ADVENTURE:
                await ctx.message.reply("Can only call this command outside of battle!")
                return

            enemy = character.hunt()

            await ctx.message.reply(f"You encounter a {enemy.name}. Do you `.fight` or `.flee`?.")

    @commands.command(name="fight", help="Fight the current enemy.")
    async def fight(self, ctx):
        user = ctx.message.author
        character = get_character_db(user.id)

        if character.mode != GameMode.BATTLE:
            await ctx.message.reply("Can only call this command in battle!")
            return
        else:
            channel = ctx.message.channel
            if not character.thread:
                thread = await channel.create_thread(name=f"{user.name}'s fight")
                character.thread = thread.id
                character.save_to_db()
                await thread.send(f"<@{user.id}>, your fight is here! Type `{BOT_PREFIX}attack` to attack an enemy.")
            else:
                thread = bot.get_channel(character.thread)
                await thread.send(f"<@{user.id}>, your fight is here! Type `{BOT_PREFIX}attack` to attack an enemy.")

    @commands.command(name="attack", help="Make an attack")
    async def attack(self, ctx, *, item_given=None):
        user = ctx.message.author
        character = get_character_db(user.id)
        thread = character.thread
        if thread == ctx.message.channel.id:

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
                        f"Enter `{BOT_PREFIX}levelup` with the stat (HP, ATTACK, DEFENSE) you would like to increase. "
                        f"e.g. "
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
                thread_channel = bot.get_channel(thread)
                await thread_channel.delete()
                channel = discord.utils.get(ctx.guild.channels, name=character.location)

                await channel.send(
                    f"{character.name} was defeated by a {enemy.name} and is no more. Rest in peace, brave adventurer.")
                return

            # No deaths, battle continues
            await ctx.message.reply(f"The battle rages on! Do you `{BOT_PREFIX}attack` or `{BOT_PREFIX}flee`?")
        else:
            await ctx.message.reply("You can't fight outside your thread.")

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

    @commands.command(name="use", help="Use item from inventory.")
    async def use(self, ctx, *, item):
        message = ctx.message
        character = get_character_db(message.author.id)
        item = get_item_db(item)

        if item.name not in character.inventory:
            await message.reply("It seems that you don't have that item or typed its name wrong. Please try again!")
        else:
            amount = character.use(item)
            if amount > 0:
                await message.reply(f"{character.name} uses {item.name}. Now you have {amount} of {item.name}.")
            else:
                await message.reply("Now you don't have that item.")

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
        if character.thread:
            channel = bot.get_channel(character.thread)
            await channel.delete()
        channel_send = discord.utils.get(ctx.guild.channels, name=character.location)
        character.die()

        await channel_send.send(f"Character {character.name} is no more. Create a new one with `{BOT_PREFIX}create`.")

    # gives only one item
    @commands.command(name="give_", help="Give a character something. For admin :3")
    @commands.has_permissions(administrator=True)
    async def give(self, ctx, user_id, *, item):
        character = get_character_db(user_id)
        if get_item_db(item):
            if item not in character.inventory:
                cursor.execute("INSERT INTO characters_inventories (user_id, title, amount) "
                               "VALUES (%s, %s, %s)", (user_id, f'{item}', 1))
            else:
                cursor.execute("SELECT amount FROM characters_inventories WHERE user_id = %s AND title = %s",
                               (user_id, f'{item}'))
                item_amount = cursor.fetchone()[0]
                cursor.execute("UPDATE characters_inventories SET amount = %s WHERE user_id = %s AND title = %s",
                               (item_amount+1, user_id, f'{item}'))

            await ctx.message.reply(f"{character.name} was blessed with {item} by gods.")
            db.commit()
        else:
            await ctx.message.reply("There is no such item.")

    # add command that changes users location and deletes thread

    # @commands.command(name="reset", help="[DEV] Destroy and recreate current character.")
    # async def reset(self, ctx):
    #     user_id = str(ctx.message.author.id)
    #
    #     # if user_id in db["characters"].keys():
    #     #     del db["characters"][user_id]
    #
    #     await ctx.message.reply(f"Character deleted.")
    #     await create(ctx)
