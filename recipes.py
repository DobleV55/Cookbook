from click.types import IntRange
from PyInquirer import style_from_dict, Token, prompt, Separator
import click
from pymongo import MongoClient
import gridfs
from bson.objectid import ObjectId
from PIL import Image
import io
import os

def connect_to_db():
    cluster = MongoClient('mongodb+srv://zkwhTxLjojbghd24jSuxiLk8GXcdL3L1c:'+os.environ.get('COOKBOOK')
+'@cookbook.5pmsh.mongodb.net/cookbook?retryWrites=true&w=majority')
    db = cluster['cookbook']
    collection = db['recipes']
    return db, collection

def send_recipe_to_db(collection, recipe):
    collection.insert_one(recipe)

def generate_recipe(db):
    title = click.prompt('Recipe Title', type=str)
    serves = click.prompt('Recipe Serves', type=IntRange(1))
    ingredients = []
    stop = 1
    print('===INGREDIENTS===')
    while stop != 0:
        ingredient = {}
        element = click.prompt('add ingredient', default="", type=str)
        if element == '':
            break
        quantity = click.prompt('add quantity (in grams)', default="", type=IntRange(1))
        if quantity == '':
            break
        ingredient[element] = quantity
        ingredients.append(ingredient)
    steps = []
    stop = 1
    counter = 1
    print('===STEPS===')
    while stop != 0:
        step = click.prompt('add step', default="", type=str)
        if step == '':
            break
        step = str(counter)+'. '+step
        counter+=1
        steps.append(step)

    image_path = click.prompt('image recipe path')
    fs = gridfs.GridFS(db)
    fileID = fs.put(open(image_path, 'rb'))
    out = fs.get(fileID)
    image = out._id

    #img = Image.open(image_path)
    #imgByteArr = io.BytesIO()
    #img.save(imgByteArr, format='PNG')
    #image = imgByteArr.getvalue()

    ### from bytearr to Image
    # image = Image.open(io.BytesIO(imgByteArr))
    # image.save('image.png')

    recipe = {}
    recipe['title'] = title
    recipe['serves'] = serves
    recipe['ingredients'] = ingredients
    recipe['steps'] = steps
    recipe['image_id'] = image
    return recipe

def main_menu():
    style = style_from_dict({
    Token.Separator: '#cc5454',
    Token.QuestionMark: '#673ab7 bold',
    Token.Selected: '#cc5454',  # default
    Token.Pointer: '#673ab7 bold',
    Token.Instruction: '',  # default
    Token.Answer: '#f44336 bold',
  })

    options = ['Add Recipe','Search Recipe','Exit']

    questions = [
                {
                  'type': 'list',
                  'message': '',
                  'name': 'option',
                  'choices':  [
                                Separator('Welcome to your Cookbook!'),
                                  {
                                    'name': options[0]
                                  },
                                  {
                                    'name': options[1]
                                  },
                                  {
                                    'name': options[2]
                                  },
                              ],
                  'validate': lambda answer: 'You must choose at least one.' \
                      if len(answer) == 0 else True
                }
              ]
    answers = prompt(questions, style=style)
    return answers, options

def search_recipe(collection, db):
    nombre = input('buscar receta: ')
    recipe = collection.find_one({'title':nombre})
    image_id = recipe['image_id']
    chunks_collection = db['fs.chunks']
    binaries = chunks_collection.find({'files_id':image_id})
    image_byn = []
    while True:
        try:
            image_byn.append(binaries.next()['data'])
        except:
            break
    image_byn = b''.join(image_byn)
    image = Image.open(io.BytesIO(image_byn))
    image.save('image.png')
    print(recipe)


if __name__ == "__main__":
    db, collection = connect_to_db()
    answers, options = main_menu()
    if answers['option'] == options[1]:
        search_recipe(collection, db)
    elif answers['option'] == options[2]:
        exit()
    elif answers['option'] == options[0]:
        recipe = generate_recipe(db)
        send_recipe_to_db(collection, recipe)
