from Content.Classes import *
from Content.Texts import *


# discord commands
class RpgBot(commands.Cog):
    def __init__(self):
        self.db = db

    def add_user_to_db(self, user_id, name, age, race, clas):
        cursor = self.db.cursor(buffered=True)
        sql_formula = ("INSERT INTO characters (user_id, name, age, race, class, location, attack, defence, money) "
                       "VALUES (%s, %s, %s, %s, %s, 'forest', 5, 5, 0)")
        cursor.execute(sql_formula, (user_id, name, age, race, clas))
        self.db.commit()

    def get_character_from_db(self, user_id):
        cursor = self.db.cursor(buffered=True)
        sql_get = f"SELECT * FROM characters WHERE user_id = {user_id}"
        cursor.execute(sql_get)
        return cursor.fetchall()

    def delete_character_from_db(self, user_id):
        cursor = self.db.cursor(buffered=True)
        sql_get = f"DELETE FROM characters WHERE user_id = {user_id}"
        cursor.execute(sql_get)
        self.db.commit()
        return

    @commands.Cog.listener()
    async def on_ready(self):
        await bot.change_presence(activity=Game(name="long swords"))
        print("[*] Connected to discord as: %s" % bot.user.name)

    @commands.command(name="profile", description="shows users info", pass_context=True)
    async def _profile(self, ctx):
        user_id = ctx.author.id
        channel = ctx.channel
        button1 = Button(label="Your character", style=ButtonStyle.gray, disabled=False)
        button2 = Button(label="Create a character!", style=ButtonStyle.red, disabled=False)
        button3 = Button(label="☠️Delete a character!", style=ButtonStyle.red, disabled=False)
        button4 = Button(label="Confirm", style=ButtonStyle.green, disabled=False)

        async def _character_info(interaction):
            res = self.get_character_from_db(user_id)
            if res:
                view.remove_item(button1)
                view.add_item(button3)
                character = Character(res[0][1], res[0][2], res[0][3], res[0][4])
                await interaction.response.edit_message(content=f"{character.print_character()}", view=view)
            else:
                view.remove_item(button1)
                view.add_item(button2)
                await interaction.response.edit_message(content="It seems that you didn't create a character!",
                                                        view=view)

        async def _character_create(interaction):
            view = View()
            await interaction.response.edit_message(content=character_create_array[0], view=view)
            msg = await bot.wait_for("message", check=lambda message: message.author == interaction.user)
            buff = [msg.content]
            await main_message.edit(content=character_create_array[1], view=view)
            msg = await bot.wait_for("message", check=lambda message: message.author == interaction.user)
            buff += [msg.content]
            view1 = ClassView()
            await main_message.edit(content="Choose a class:", view=view1)
            await view1.wait()
            view = RaceView()
            await main_message.edit(content="Choose a race:", view=view)
            await view.wait()
            character = Character(name=buff[0], age=buff[1], race=view.answer.values[0], clas=view1.answer1.values[0])
            await channel.send(character.print_character())
            self.add_user_to_db(user_id, character.name, character.age, character.race, character.clas)

        async def _character_delete(interaction):
            view.remove_item(button3)
            view.add_item(button4)
            await interaction.response.send_message(content="Are you sure you want to delete this character?",
                                                    view=view)

        async def confirm(interaction):
            view.remove_item(button4)
            try:
                self.delete_character_from_db(user_id)
            except Exception as e:
                await interaction.response.edit_message(content="Something went wrong!", view=view)
                raise e
            await interaction.response.edit_message(content="Your character was deleted successfully!", view=view)

        button1.callback = _character_info
        button2.callback = _character_create
        button3.callback = _character_delete
        button4.callback = confirm
        view = View()
        view.add_item(button1)

        main_message = await ctx.reply("👀 Oh no! There is only one button...", view=view)

    @commands.command(name="rpg", description="starts the rpg session", pass_context=True)
    async def _rpg(self, ctx):
        user_id = ctx.author.id
        channel = ctx.channel


def _db_to_class(value: dict):
    character = Character_(name=value["name"],
                           hp=value["hp"],
                           max_hp=value["max_hp"],
                           attack=value["attack"],
                           defense=value["defense"],
                           xp=value["xp"],
                           gold=value["gold"],
                           inventory=value["inventory"],
                           mana=value["mana"],
                           level=value["level"],
                           mode=value["mode"],
                           battling=value["battling"],
                           location=value["location"],
                           user_id=value["user_id"])

    return character


def _get_character_db(_id):
    cursor = db.cursor(dictionary=True, buffered=True)  # returns db in dictionary style
    sql_get = f"SELECT * FROM characters_2 WHERE user_id = {_id}"
    cursor.execute(sql_get)
    res = cursor.fetchall()
    if res:
        return _db_to_class(res[0])
    else:
        return None


def _add_character_db(character):
    cursor = db.cursor(buffered=True)
    sql_insert = ("INSERT INTO characters_2 (name, hp, max_hp, attack, defense, xp, gold, inventory, mana, level, "
                  "mode, battling, location, user_id) "
                  "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
    cursor.execute(sql_insert, list(vars(character).values()))
    db.commit()


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

    embed.add_field(name="Stats", value=f"""
    **HP:**    {character.hp}/{character.max_hp}
    **ATTACK:**   {character.attack}
    **DEFENSE:**   {character.defense}
    **MANA:**  {character.mana}
    **LEVEL:** {character.level}
    **XP:**    {character.xp}/{character.xp + xp_needed}
        """, inline=True)

    embed.add_field(name="", value="")

    # Inventory field
    inventory_text = f"Gold: {character.gold}\n"
    inventory = character.inventory.split(',')
    if inventory:
        inventory_text += "\n".join(inventory)

    embed.add_field(name="Inventory", value=inventory_text, inline=True)

    return embed


class rpg(commands.Cog):

    @commands.command(name="create", help="Create a character")
    async def _create(self, ctx, name=None):
        if ctx.channel.id == 1224681797179281458:
            user_id = ctx.message.author.id

            # if no name is specified, use the creator's nickname
            if not name:
                name = ctx.message.author.name

            if _get_character_db(user_id):
                await ctx.reply(f"You already have a character! Check the **{BOT_PREFIX}status** command.")
            else:
                character = Character_(name=name,
                                       hp=16,
                                       max_hp=16,
                                       attack=2,
                                       defense=1,
                                       xp=0,
                                       gold=1,
                                       inventory="Sword, Shield",
                                       mana=0,
                                       level=0,
                                       mode=GameMode.ADVENTURE,
                                       battling=None,
                                       location="forest",
                                       user_id=user_id)
                try:
                    _add_character_db(character)
                except Exception:
                    await ctx.reply(content="Something went wrong. Please try again.")
                    raise Exception("Couldn't save character to a database")
                finally:
                    channel = bot.get_channel(1224635518839554099)
                    print(ctx.author)
                    await channel.set_permissions(ctx.author, read_messages=True, send_messages=True)
                    await ctx.reply(content=f"Your character has been created successfully!\nYou are now located in the "
                                            f"forest.\nCheck the **{BOT_PREFIX}status** command.")

        else:
            await ctx.reply(content="This command should be used in `character-creation` channel.")

    @commands.command(name="status", help="Get information about your character")
    async def _status(self, ctx):
        character = _get_character_db(ctx.message.author.id)

        if character:
            embed = status_embed(ctx, character)
            await ctx.message.reply(embed=embed)
        else:
            await ctx.reply(content=f"You don't have a character! Check the **{BOT_PREFIX}create** command")

    @commands.command(name="explore", help="search for enemies in your location")
    async def _explore(self, ctx):
        await ctx.message.reply(content="This command is under development.")

    @commands.command(name="hunt", help="Look for an enemy to fight.")
    async def _hunt(self, ctx):
        character = _get_character_db(ctx.message.author.id)

        if character.mode != GameMode.ADVENTURE:
            await ctx.message.reply("Can only call this command outside of battle!")
            return

        enemy = character.hunt()

        # Send reply
        await ctx.message.reply(f"You encounter a {enemy.name}. Do you `.fight` or `.flee`?. This command will work in "
                                f"several days!")

    @commands.command(name="level_up", help="Level up your character.")
    async def _level_up(self, ctx, increase):
        character = _get_character_db(ctx.message.author.id)
        if character:
            if character.mode != GameMode.ADVENTURE:
                await ctx.message.reply("Can only call this command outside of battle!")
                return

            ready, xp_needed = character.ready_to_level_up()
            if not ready:
                await ctx.message.reply(f"You need another {xp_needed} to advance to level {character.level + 1}")
                return

            if not increase:
                await ctx.message.reply("Please specify a stat to increase (HP, ATTACK, DEFENSE)")
                return
        else:
            await ctx.reply(content=f"You don't have a character! Check the **{BOT_PREFIX}create** command")


bot.add_cog(RpgBot())
bot.add_cog(rpg())
bot.run(BOT_TOKEN)
