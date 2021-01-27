from click.types import FloatRange, IntRange
from PyInquirer import style_from_dict, Token, prompt, Separator
import click
from pymongo import MongoClient
import gridfs
from PIL import Image
import io
import os


def connect_to_db():
    cluster = MongoClient('mongodb+srv://zkwhTxLjojbghd24jSuxiLk8GXcdL3L1c:'+str(os.environ['COOKBOOK'])+'@cookbook.5pmsh.mongodb.net/cookbook?retryWrites=true&w=majority')
    db = cluster['cookbook']
    collection = db['recipes']
    return db, collection


def send_recipe_to_db(collection, recipe, childs_recipes):
    collection.insert_one(recipe)
    for child_recipe in childs_recipes:
        collection.insert_one(child_recipe)


def generate_recipe(db):
    title = click.prompt('Recipe Title', type=str)
    serves = click.prompt('Recipe Serves', type=IntRange(1))
    childs_titles = []
    childs_recipes = []
    while True:
        title_child = click.prompt('Child Title', default="", type=str)
        if title_child == '':
            break
        childs_titles.append(title_child)
        ingredients = {}
        stop = 1
        print('===INGREDIENTS===')
        while stop != 0:
            element = click.prompt('add ingredient', default="", type=str)
            if element == '':
                break
            quantity = click.prompt('add quantity', default="", type=FloatRange(0))
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
            counter += 1
            steps.append(step)

        child_recipe = {}
        child_recipe['title'] = title_child
        child_recipe['ingredients'] = ingredients
        child_recipe['steps'] = steps
        child_recipe['is_mother'] = False
        childs_recipes.append(child_recipe)
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
    recipe['is_mother'] = True
    recipe['childs'] = childs_titles
    recipe['image_id'] = image

    return recipe, childs_recipes


def main_menu():
    style = style_from_dict({
    Token.Separator: '#cc5454',
    Token.QuestionMark: '#673ab7 bold',
    Token.Selected: '#cc5454',  # default
    Token.Pointer: '#673ab7 bold',
    Token.Instruction: '',  # default
    Token.Answer: '#f44336 bold',
  })

    options = ['Add Recipe', 'Search Recipe', 'List Recipes', 'Edit Recipe', 'Exit']
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
                                    # Add image to recipe / change image for recipe / change parameters to recipe
                                  },
                                  {
                                    'name': options[4]
                                  }
                              ],
                  'validate': lambda answer: 'You must choose at least one.' \
                }
              ]
    answers = prompt(questions, style=style)
    return answers, options


def search_recipe(collection, db, title):
    if title is None:
        title = click.prompt('buscar receta: ', type=str)
    recipe = collection.find_one({'title': title, 'is_mother': True})
    if recipe is None:
        print('Thats not a valid recipe title')
        return
    childs_recipes = []
    for child_recipe in recipe['childs']:
        childs_recipes.append(collection.find_one({'title': child_recipe, 'is_mother':False}))
    image_id = recipe['image_id']
    if image_id is None:
        serves = click.prompt('How many serves?', type=IntRange(1), default=recipe['serves'])
        show_recipe(recipe, childs_recipes, image_id, serves)
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
        show_recipe(recipe, childs_recipes, image, serves)


def list_recipes(collection):
    recipe_titles = []
    recipes = collection.find({'is_mother': True})
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


def show_recipe(recipe, childs_recipes, image, serves):
    print(f"\n{recipe['title']}")
    print(f"\nServes: {serves}")
    for child_recipe in childs_recipes:
        print(f'\n{child_recipe["title"]}')
        print('\nIngredients:')
        for ingredient, quantity in child_recipe['ingredients'].items():
            if type(quantity) is int:
                print('-', ingredient)
            else:
                qua = quantity.split(' ')[0]
                try:
                    qua = int(qua)
                except:
                    qua = float(qua)
                qua = serves*qua/recipe['serves']
                qua = round(qua,1)
                measurement = quantity.split(' ')[1]
                if int(qua) == 0:
                    print('-', qua, measurement, ingredient)
                else:
                    print('-', int(qua), measurement, ingredient)
        print(f"\nSteps:")
        for step in child_recipe['steps']:
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
        recipe, childs_recipes = generate_recipe(db)
        send_recipe_to_db(collection, recipe, childs_recipes)
