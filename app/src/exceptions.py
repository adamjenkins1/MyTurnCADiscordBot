"""Contains various custom exceptions"""
from discord.ext import commands


class InvalidZipCode(commands.BadArgument):
    """Exception to be thrown if the provided zip code was not valid"""
    pass