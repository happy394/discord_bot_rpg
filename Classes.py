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
