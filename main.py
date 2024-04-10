from Content.Classes import bot, Rpg, BOT_TOKEN

if __name__ == '__main__':
    bot.add_cog(Rpg())
    bot.run(BOT_TOKEN)
