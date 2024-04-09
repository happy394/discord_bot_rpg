from Content.Classes import *


class RpgBot(commands.Cog):
    pass
    # def __init__(self):
    #     self.db = db

    # def add_user_to_db(self, user_id, name, age, race, clas):
    #     cursor = self.db.cursor(buffered=True)
    #     sql_formula = ("INSERT INTO characters (user_id, name, age, race, class, location, attack, defence, money) "
    #                    "VALUES (%s, %s, %s, %s, %s, 'forest', 5, 5, 0)")
    #     cursor.execute(sql_formula, (user_id, name, age, race, clas))
    #     self.db.commit()

    # def get_character_from_db(self, user_id):
    #     cursor = self.db.cursor(buffered=True)
    #     sql_get = f"SELECT * FROM characters WHERE user_id = {user_id}"
    #     cursor.execute(sql_get)
    #     return cursor.fetchall()
    #
    # def delete_character_from_db(self, user_id):
    #     cursor = self.db.cursor(buffered=True)
    #     sql_get = f"DELETE FROM characters WHERE user_id = {user_id}"
    #     cursor.execute(sql_get)
    #     self.db.commit()
    #     return
    #
    # @commands.Cog.listener()
    # async def on_ready(self):
    #     await bot.change_presence(activity=Game(name="long swords"))
    #     print("[*] Connected to discord as: %s" % bot.user.name)
    #
    # @commands.command(name="profile", description="shows users info", pass_context=True)
    # async def _profile(self, ctx):
    #     user_id = ctx.author.id
    #     channel = ctx.channel
    #     button1 = Button(label="Your character", style=ButtonStyle.gray, disabled=False)
    #     button2 = Button(label="Create a character!", style=ButtonStyle.red, disabled=False)
    #     button3 = Button(label="☠️Delete a character!", style=ButtonStyle.red, disabled=False)
    #     button4 = Button(label="Confirm", style=ButtonStyle.green, disabled=False)
    #
    #     async def _character_info(interaction):
    #         res = self.get_character_from_db(user_id)
    #         if res:
    #             view.remove_item(button1)
    #             view.add_item(button3)
    #             character = Character(res[0][1], res[0][2], res[0][3], res[0][4])
    #             await interaction.response.edit_message(content=f"{character.print_character()}", view=view)
    #         else:
    #             view.remove_item(button1)
    #             view.add_item(button2)
    #             await interaction.response.edit_message(content="It seems that you didn't create a character!",
    #                                                     view=view)
    #
    #     async def _character_create(interaction):
    #         view = View()
    #         await interaction.response.edit_message(content=character_create_array[0], view=view)
    #         msg = await bot.wait_for("message", check=lambda message: message.author == interaction.user)
    #         buff = [msg.content]
    #         await main_message.edit(content=character_create_array[1], view=view)
    #         msg = await bot.wait_for("message", check=lambda message: message.author == interaction.user)
    #         buff += [msg.content]
    #         view1 = ClassView()
    #         await main_message.edit(content="Choose a class:", view=view1)
    #         await view1.wait()
    #         view = RaceView()
    #         await main_message.edit(content="Choose a race:", view=view)
    #         await view.wait()
    #         character = Character(name=buff[0], age=buff[1], race=view.answer.values[0], clas=view1.answer1.values[0])
    #         await channel.send(character.print_character())
    #         self.add_user_to_db(user_id, character.name, character.age, character.race, character.clas)
    #
    #     async def _character_delete(interaction):
    #         view.remove_item(button3)
    #         view.add_item(button4)
    #         await interaction.response.send_message(content="Are you sure you want to delete this character?",
    #                                                 view=view)
    #
    #     async def confirm(interaction):
    #         view.remove_item(button4)
    #         try:
    #             self.delete_character_from_db(user_id)
    #         except Exception as e:
    #             await interaction.response.edit_message(content="Something went wrong!", view=view)
    #             raise e
    #         await interaction.response.edit_message(content="Your character was deleted successfully!", view=view)
    #
    #     button1.callback = _character_info
    #     button2.callback = _character_create
    #     button3.callback = _character_delete
    #     button4.callback = confirm
    #     view = View()
    #     view.add_item(button1)
    #
    #     main_message = await ctx.reply("👀 Oh no! There is only one button...", view=view)
    #
    # @commands.command(name="rpg", description="starts the rpg session", pass_context=True)
    # async def _rpg(self, ctx):
    #     user_id = ctx.author.id
    #     channel = ctx.channel


def create_character_db(character):
    cursor = db.cursor()
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


def get_character_db(_id):
    cursor = db.cursor()
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


bot = commands.Bot(command_prefix=BOT_PREFIX, intents=Intents.all())
MODE_COLOR = {
    GameMode.BATTLE: 0xDC143C,
    GameMode.ADVENTURE: 0x005EB8,
}


def status_embed(ctx, character):
    mode_text = ""
    # Current mode
    if character.mode == GameMode.BATTLE:
        mode_text = f"Currently battling a {character.battling.name}."
    elif character.mode == GameMode.ADVENTURE:
        mode_text = "Currently adventuring."

    # Create embed with description as current mode
    embed = discord.Embed(title=f"{character.name} status", description=mode_text, color=MODE_COLOR[character.mode])
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


class Rpg(commands.Cog):

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
                f"{character.name} was killed fleeing the {enemy.name}, and is no more. Rest in peace, brave adventurer.")
        elif damage:
            await ctx.message.reply(
                f"{character.name} flees the {enemy.name}, taking {damage} damage. HP: {character.hp}/{character.max_hp}")
        else:
            await ctx.message.reply(
                f"{character.name} flees the {enemy.name} with their life but not their dignity intact. HP: {character.hp}/{character.max_hp}")

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


# bot.add_cog(RpgBot())
bot.add_cog(Rpg())
bot.run(BOT_TOKEN)
