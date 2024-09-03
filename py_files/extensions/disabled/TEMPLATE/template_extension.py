# Template


# This is like any other Python file essentially.
class Greeter:
    def __init__(self) -> None:
        pass

    def hello(self) -> None:
        print("Hello World!")


# setup() and teardown() are required.
async def setup(bot):
    # If you want to interact with the bot, you can get
    # a reference to it from here.
    pass


async def teardown(bot):
    # Any cleanup that is required can be done here.
    pass
