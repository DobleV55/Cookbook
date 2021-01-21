from click.types import IntRange
from PyInquirer import style_from_dict, Token, prompt, Separator
import click
from pymongo import MongoClient
import gridfs
from PIL import Image
import io
import os

def connect_to_db():
    cluster = MongoClient('mongodb+srv://zkwhTxLjojbghd24jSuxiLk8GXcdL3L1c:'+str(os.environ.get('COOKBOOK'))
+'@cookbook.5pmsh.mongodb.net/cookbook?retryWrites=true&w=majority')
    db = cluster['cookbook']
    collection = db['recipes']
    return db, collection

def send_recipe_to_db(collection, recipe):
    collection.insert_one(recipe)

def generate_recipe(db):
    title = click.prompt('Recipe Title', type=str)
    serves = click.prompt('Recipe Serves', type=IntRange(1))
    ingredients = {}
    stop = 1
    print('===INGREDIENTS===')
    while stop != 0:
        element = click.prompt('add ingredient', default="", type=str)
        if element == '':
            break
        quantity = click.prompt('add quantity (in grams)', default="", type=IntRange(0))
        if quantity == 0:
            ingredients[element] = quantity
            pass
        elif quantity == '':
            break
        else:
            measures = [
            {
            'type': 'list',
            'name': 'measurement',
            'message': 'grams or units?',
            'choices': ['grams','units','cups'],
            },]
            measurement = prompt(measures)['measurement']
            quantity = f'{quantity} {measurement}'
            ingredients[element] = quantity
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

    print('===IMAGE===')
    image_path = click.prompt('image recipe path')
    fs = gridfs.GridFS(db)
    image = None
    try:
        fileID = fs.put(open(image_path, 'rb'))
        out = fs.get(fileID)
        image = out._id
    except:
        print('no image with that name, recipe has been uploaded without image')

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

    options = ['Add Recipe','Search Recipe','List Recipes','Edit Recipe','Exit']
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
                                  {
                                    'name': options[3],
                                    'disabled': 'Unavailable at this time'
                                  },
                                  {
                                    'name': options[4]
                                  }
                              ],
                  'validate': lambda answer: 'You must choose at least one.' \
                      if len(answer) == 0 else True
                }
              ]
    answers = prompt(questions, style=style)
    return answers, options


def search_recipe(collection, db, title):
    if title is None:
        title = click.prompt('buscar receta: ', type=str)
    recipe = collection.find_one({'title': title})
    image_id = recipe['image_id']
    if recipe is None:
        print('Thats not a valid recipe title')
        return
    if image_id is None:
        serves = click.prompt('How many serves?', type=IntRange(1), default=recipe['serves'])
        show_recipe(recipe, image_id, serves)
    else:    
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
        serves = click.prompt('How many serves?', type=IntRange(1), default=recipe['serves'])
        show_recipe(recipe, image, serves)


def list_recipes(collection):
    recipe_titles = []
    recipes = collection.find()
    while True:
        try:
            recipe_titles.append(recipes.next()['title'])
        except:
            break
    questions = [
    {
        'type': 'list',
        'name': 'title',
        'message': 'Recipes from Cookbook',
        'choices': sorted(recipe_titles)
    },
    ]
    answers = prompt(questions)['title']
    return answers


def show_recipe(recipe, image, serves):
    print(f"\n{recipe['title']}")
    print(f"\nServes: {serves}")
    print(f"\nIngredients:")
    for ingredient, quantity in recipe['ingredients'].items():
        if type(quantity) is int:
            print('-', ingredient)
        else:
            qua = quantity.split(' ')[0]
            qua = serves*int(qua)/recipe['serves']
            measurement = quantity.split(' ')[1]
            if int(qua) == 0:
                print('-', qua, measurement, ingredient)
            else:
                print('-', int(qua), measurement, ingredient)
    print(f"\nSteps:")
    for step in recipe['steps']:
        print(step)
    if image is None:
        print('\nNo image for this Recipe!')
    else:
        image_name = recipe['title'].lower().replace(' ', '_')
        image.save(f'{image_name}.png')
        image_path = f'{os.getcwd()}/{image_name}'
        print(f'\nLook the image for the recipe located at {image_path}')

if __name__ == "__main__":
    db, collection = connect_to_db()
    answers, options = main_menu()
    recipe = None
    if answers['option'] == options[1]:
        search_recipe(collection, db, recipe)
    elif answers['option'] == options[2]:
        recipe = list_recipes(collection)
        search_recipe(collection, db, recipe)
    elif answers['option'] == options[4]:
        exit()
    elif answers['option'] == options[0]:
        recipe = generate_recipe(db)
        send_recipe_to_db(collection, recipe)
