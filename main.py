# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

from openai import OpenAI
import pandas as pd

df = pd.read_excel("StocksTable.xlsx")
client = OpenAI('API-KEY')
 
response = client.responses.create(
    model="gpt-3.5-turbo",
    input="Write a one-sentence bedtime story about a unicorn."
)

print(response.output_text)
