import mysql.connector

from settings import *
from Content.Classes import *
from Content.Texts import *


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


# discord commands
class RpgBot(commands.Cog):
    def __init__(self):
        self.db = connect_database()

    def add_user_to_db(self, user_id, name, age, race, clas):
        cursor = self.db.cursor(buffered=True)
        sql_formula = ("INSERT INTO characters (user_id, name, age, race, class, attack, defence, money) "
                       "VALUES (%s, %s, %s, %s, %s, 5, 5, 0)")
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

    @commands.command(name="profile", description="starts the rpg session", pass_context=True)
    async def profile(self, ctx):
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

# TODO 1. make confirm button inside 3rd button
# TODO 2. create class to search for loot based on location


bot = commands.Bot(command_prefix=BOT_PREFIX, intents=Intents.all())
bot.add_cog(RpgBot())
bot.run(BOT_TOKEN)
