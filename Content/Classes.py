import discord
from discord import Game, Intents, ButtonStyle
from discord.ui import View, Button
from discord.ext import commands


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

