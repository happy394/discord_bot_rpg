from Content.Classes import bot, BOT_TOKEN
from bot import Rpg

if __name__ == '__main__':
    bot.add_cog(Rpg())
    bot.run(BOT_TOKEN)
