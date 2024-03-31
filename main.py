import mysql.connector

from settings import *
from Classes import *
from Texts import *

from discord import Game, Intents, ButtonStyle
from discord.ui import View, Button
from discord.ext import commands


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


# connect to discord
class RpgBot(commands.Cog):
    def __init__(self):
        self.db = connect_database()

    def add_user_to_db(self, user_id, name, age, race, clas):
        cursor = self.db.cursor(buffered=True)
        sql_formula = ("INSERT INTO characters (user_id, name, age, race, class, attack, defence) "
                       "VALUES (%s, %s, %s, %s, %s, 5, 5)")
        cursor.execute(sql_formula, (user_id, name, age, race, clas))
        self.db.commit()

    def get_character_from_db(self, user_id):
        cursor = self.db.cursor(buffered=True)
        sql_get = f"SELECT * FROM characters WHERE user_id = {user_id}"
        cursor.execute(sql_get)
        return cursor.fetchall()

    @commands.Cog.listener()
    async def on_ready(self):
        await bot.change_presence(activity=Game(name="long swords"))
        print("[*] Connected to discord as: %s" % bot.user.name)

    @commands.command(name="rpg", description="starts the rpg session", pass_context=True)
    async def rpg(self, ctx):
        user_id = ctx.author.id
        channel = ctx.channel
        button1 = Button(label="Your character", style=ButtonStyle.gray, disabled=False)
        button2 = Button(label="Create a character!", style=ButtonStyle.red, disabled=False)

        async def _character_info(interaction):
            res = self.get_character_from_db(user_id)
            if res:
                await interaction.response.edit_message(content="Here is your character:")
                character = Character(res[0][1], res[0][2], res[0][3], res[0][4])
                await channel.send(character.print_character())
            else:
                view.remove_item(button1)
                view.add_item(button2)
                await interaction.response.edit_message(content="It seems that you didn't create a character!",
                                                        view=view)

        async def _character_create(interaction):
            await interaction.response.send_message("Let's start.")
            buff = []
            # for i in range(0, len(character_create_array)):
            for i in range(0, 1):
                await channel.send(character_create_array[i])
                msg = await bot.wait_for("message", check=lambda message: message.author == interaction.user)
                buff.append(msg.content)
            # character = Character(name=buff[0], age=buff[1], race=buff[2], clas=buff[3])
            character = Character(name=buff[0], age=19, race="Human", clas="Warrior")
            await channel.send(character.print_character())
            self.add_user_to_db(user_id, character.name, character.age, character.race, character.clas)

        button1.callback = _character_info
        button2.callback = _character_create
        view = View()
        view.add_item(button1)

        await ctx.reply("Hmmm... What should we do?", view=view)


bot = commands.Bot(command_prefix=BOT_PREFIX, intents=Intents.all())
bot.add_cog(RpgBot())
bot.run(BOT_TOKEN)
