import os
import logging, datetime
from peewee import DatabaseError
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import filters
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher import FSMContext
from keyboards import *
from states import *
from constants import *
from models import db, Task
import re

API_TOKEN = '6065585416:AAGyFxzNhsekSrFWfjaC3ubj8hzHDIaHKrc'

#logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

db.create_tables([Task])

@dp.message_handler(commands=['start'], state = "*")
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer('hello',reply_markup=start_kb)



@dp.message_handler(Text(equals='add new task'), state=None)
async def new_task_handler(message: types.Message):
    await TaskState.header.set()
    await message.answer('please input task header', reply_markup=cancel_kb)



@dp.message_handler(Text(equals='show current tasks'), state=None)
async def show_cur_tasks(message: types.Message):
    query = Task.select().where(Task.is_finished == False)
    if len(query) == 0:
        await message.reply('there is no current tasks')
    else:
        for row in query:
            await bot.send_message(chat_id= message.from_user.id, text=f'header: {str(row.header)} \n description: {str(row.description)} \n date: {str(row.date)}')
    await bot.send_message(chat_id= message.from_user.id, text='wanna edit some task? write "edit <header> <option> to continue" ')
    await EditState.check.set()

@dp.message_handler(commands=['cancel'], state = "*")
async def cmd_cancel(message: types.Message, state: FSMContext):
    print(await state.get_state())
    if await state.get_state() == None:
        await bot.send_message(chat_id= message.from_user.id, text='no state to cancel. input correct command')
    else:
        print("Cancelling state...")
        current_state = await state.get_state()
        if current_state is None:
            return
        await state.finish()
        await message.answer('state cancelled',reply_markup=cancel_kb)



@dp.message_handler(content_types = types.ContentTypes.ANY, state=EditState.check)
async def handle_wrong_msg(message: types.Message, state:FSMContext):
    data = await state.get_data()
    if message.text is not None:
        options_list = message.text.split()
        if message.caption is None and message.text.startswith('edit '):
            tasks = Task.select().where(Task.header == options_list[1])
            if len(tasks) != 0:
                if len(options_list) == 3:
                    async with state.proxy() as data:
                            data['edit_id'] = tasks[0].id
                            print('the id is:', tasks[0].id)
                    if options_list[2] == 'description':
                        await EditState.description.set()
                        await message.reply('input new description')
                    elif options_list[2] == 'date':
                        await EditState.date.set()
                        await message.reply('input new date')
                    elif options_list[2] == 'time':
                        await EditState.time.set()
                        await message.reply('input new time')
                    elif options_list[2] == 'attachments':
                        await EditState.attachments.set()
                        path = f'storage/attachments/{tasks[0].id}'

                        if os.path.isdir(path):
                            print(f'{tasks[0].id}')
                            files = os.listdir(f'storage/attachments/{tasks[0].id}')
                            if files:
                                filenames = '\n'.join(files)
                                await bot.send_message(chat_id= message.from_user.id, text=f'your attachments are: \n' + filenames)
                            else:
                                await bot.send_message(chat_id= message.from_user.id, text='you have no attachments yet. (emptydir)')
                        else:
                            await bot.send_message(chat_id= message.from_user.id, text=f'you have no attachments yet. (nodir)')
                        await bot.send_message(chat_id= message.from_user.id, text=f'to delete file, input command: \n delete <filename> \n delete all. to add file, drag`n`drop file here')
                    else:
                        await message.reply('there`s no such option')
                else:
                    await message.reply('wanna edit some task? write "edit <header> <option> to continue"')
            else:
                await message.reply('there`s no such header')
        else:
            await message.reply('wanna edit some task? write "edit <header> <option> to continue"')
    else:
        await message.reply('wanna edit some task? write "edit <header> <option> to continue"')



@dp.message_handler(content_types = types.ContentTypes.ANY, state=None)
async def handle_wrong_msg(message: types.Message):
    await message.reply('input correct command')

@dp.message_handler(content_types=types.ContentTypes.TEXT, state=TaskState.header)
async def header_check_save(message: types.Message, state: FSMContext):
    tasks = None
    try:
        tasks = Task.select().where(Task.header == message.text)
    except Exception as e:
        print(type(e).__name__, e)
    if tasks.count() == 0:
        async with state.proxy() as data:
            data['header'] = message.text
        await TaskState.next()
        await message.reply('header accepted. input description')
    else:
        await message.reply('header must be unique')

@dp.message_handler(content_types=types.ContentTypes.ANY, state=TaskState.header)
async def header_check_any(message: types.Message):
   return await message.reply('it doesnt look like header (any)')



@dp.message_handler(content_types=types.ContentTypes.TEXT, state=[TaskState.description, EditState.description])
async def desc_check_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if await state.get_state() == 'TaskState:description':
        print('descr taskstate reached')
        async with state.proxy() as data:
            data['description'] = message.text
        await TaskState.next()
        await message.reply('description accepted. input date YYYY-MM-DD')
    elif await state.get_state() == 'EditState:description':
        try:
            Task.update(description = message.text).where(Task.id == data['edit_id']).execute()
            async with state.proxy() as data:
                data['edit_id'] = None  
        except Exception as e:
            print(type(e).__name__, e)
        print('descr editstate reached')
        await bot.send_message(chat_id= message.from_user.id, text='description successfully edited!')
        await EditState.check.set()
    else:
        print('why (descr)')

@dp.message_handler(content_types=types.ContentTypes.ANY, state=[TaskState.description, EditState.description])
async def desc_check_any(message: types.Message):

    return await message.reply('it doesnt look like description (any)')



@dp.message_handler(filters.Regexp(r'^\d{4}-\d{2}-\d{2}$'), state=[TaskState.date, EditState.date])
async def date_check_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if await state.get_state() == 'TaskState:date':
        try:
            date = datetime.datetime.strptime(message.text, date_format).date()
        except ValueError:
            await message.reply('date format must be YYYY-MM-DD')
            return
        async with state.proxy() as data:
            data['date'] = date
        await TaskState.next()
        await message.reply('date accepted. input time HH:MM:SS')
    elif await state.get_state() == 'EditState:date':
        try:
            Task.update(date = message.text).where(Task.id == data['edit_id']).execute()
            async with state.proxy() as data:
                data['edit_id'] = None 
        except Exception as e:
            print(type(e).__name__, e)
        print('date editstate reached')
        await bot.send_message(chat_id= message.from_user.id, text='date successfully edited!')
        await EditState.check.set()
    else:
        print('why')


@dp.message_handler(content_types=types.ContentTypes.ANY, state=[TaskState.date, EditState.date])
async def date_check_any(message: types.Message):
    return await message.reply('it doesnt look like date (any)')


@dp.message_handler(filters.Regexp(r'^\d{2}:\d{2}:\d{2}$'), state=[TaskState.time, EditState.time])
async def time_check_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if await state.get_state() == 'TaskState:time':
        try:
            time = datetime.datetime.strptime(message.text, time_format).time()
        except ValueError:
            await message.reply('time format must be HH:MM::SS')
            return
        async with state.proxy() as data:
            data['time'] = time
        await TaskState.next()
        await message.reply('time accepted. is your task periodic [yes/no]?')
    elif await state.get_state() == 'EditState:time':
        try:
            Task.update(time = message.text).where(Task.id == data['edit_id']).execute()
            async with state.proxy() as data:
                data['edit_id'] = None 
        except Exception as e:
            print(type(e).__name__, e)
        print('time editstate reached')
        await bot.send_message(chat_id= message.from_user.id, text='date successfully edited!')
        await EditState.check.set()
    else:
        print('why (time)')
@dp.message_handler(content_types=types.ContentTypes.ANY, state=[TaskState.time, EditState.time])
async def time_check_any(message: types.Message):
    return await message.reply('it doesnt look like time (any)')

@dp.message_handler(content_types=types.ContentTypes.ANY, state=TaskState.is_periodic)
async def periodic_question(message: types.Message, state: FSMContext):
    print('periodic')
    data = await state.get_data()
    pattern = r'^\d+$'
    if message.text == 'no' and not data.get('is_periodic'):
        async with state.proxy() as data:
            data['is_periodic'] = False
            data['interval'] = None
        await TaskState.next()
        await bot.send_message(chat_id= message.from_user.id, text='ok. need to add attachments [yes/no] ?')
    elif message.text == 'yes':
        async with state.proxy() as data:
            data['is_periodic'] = True
        await message.reply('what`s the interval of task notification (in hrs) ?')    
    elif data.get('is_periodic'):
        if (message.text is not None) and bool(re.match(pattern, message.text)):
            async with state.proxy() as data:
                data['interval'] = int(message.text)
            await TaskState.next()
            await bot.send_message(chat_id= message.from_user.id, text='ok. need to add attachments [yes/no] (per)?')
        else:
            await message.reply('interval load error')
    else:
        await message.reply('is your task periodic [yes/no] ?') 



@dp.message_handler(content_types=types.ContentTypes.ANY, state=[TaskState.attachments, EditState.attachments])
async def attachments_choice(message: types.Message, state: FSMContext):
    if await state.get_state() == 'TaskState:attachments':
        data = await state.get_data()
        task = None
        if message.text == 'no' and 'attachments' not in data:
            try:
                task = Task.create(user_id=message.from_user.id, header=data['header'], description=data['description'],
                            date=data['date'], time=data['time'], is_periodic = data['is_periodic'], interval = data['interval'],
                            is_finished = False)
            except Exception as e:
                print(type(e).__name__, e)
            await state.finish()
            await message.reply('ok. task registered !')
        elif message.text == 'yes' and ('attachments' not in data):
            async with state.proxy() as data:
                data['attachments'] = True
            await message.reply('load your files')
        elif data.get('attachments'):
            if message.caption is None and (message.document is not None):
                if 'id' in data:
                    task = Task.get_by_id(data['id'])
                if task is None:
                    try:
                        task = Task.create(user_id=message.from_user.id, header=data['header'], description=data['description'],
                            date=data['date'], time=data['time'], is_periodic = data['is_periodic'], interval = data['interval'],
                                attachments = data['attachments'], is_finished = False)
                    except Exception as e:
                        print(type(e).__name__, e)
                    async with state.proxy() as data:
                        data['id'] = task.id  
                    os.makedirs(f"storage/attachments/{data['id']}")
                    notification_id = data['id']
                    await message.document.download(os.path.join(f'storage/attachments/{notification_id}', message.document.file_name))
                    await message.reply('doc loaded (later). if there`s no files more, press "enough"')
                else:
                    task = Task.get_by_id(data['id'])
                    notification_id = data['id']
                    await message.document.download(os.path.join(f'storage/attachments/{notification_id}', message.document.file_name))
                    await message.reply('doc loaded (later). if there`s no files more, press "enough"')
            elif message.text != 'enough' and message.text is not None:
                await message.reply('text is not accepted. send files only')
            elif data.get('attachments') and message.text == 'enough':
                print(data.get('attachments'))
                print(message.text)
                if 'id' not in data:
                    await message.reply('send at least one attachment to continue')
                else:
                    await message.reply('ok. task registered !')
                    await state.finish()
            elif message.text != 'enough':
                await message.reply('attachment load error')
        else:
            await message.reply('need to add attachments [yes/no] ?') 
    elif await state.get_state() == 'EditState:attachments':
        data = await state.get_data()
        edit_id = data['edit_id']
        if message.text is not None:
            options_list = message.text.split()
            if message.caption is None and message.text.startswith('delete '):
                if len(options_list) == 2:
                        print(options_list[1])
                        if message.caption is None and message.text == 'delete all':
                            try:
                                if len(os.listdir(f'storage/attachments/{edit_id}')) == 0:
                                    return await bot.send_message(chat_id= message.from_user.id, text='nothing to delete. add files by drag`n`drop')
                                else:
                                    for file in os.listdir(f'storage/attachments/{edit_id}'):
                                        try:
                                            if os.path.isfile(os.path.join(f'storage/attachments/{edit_id}', file)):
                                                os.remove(os.path.join(f'storage/attachments/{edit_id}', file))
                                        except Exception as e:
                                            print(type(e).__name__+ ' inner', e, + 'inner')
                                    await bot.send_message(chat_id= message.from_user.id, text='delete successful')            
                            except Exception as e:
                                print(type(e).__name__ + ' outer', e)
                                await bot.send_message(chat_id= message.from_user.id, text='nothing to delete. add files by drag`n`drop')
                        else:
                            file_to_del = options_list[1]
                            try:
                                if len(os.listdir(f'storage/attachments/{edit_id}')) == 0:
                                    return await bot.send_message(chat_id= message.from_user.id, text='nothing to delete. add files by drag`n`drop')
                                os.remove(os.path.join(f'storage/attachments/{edit_id}', file_to_del))
                            except Exception as e:
                                print(type(e).__name__, e)
                                await bot.send_message(chat_id= message.from_user.id, text='there is no such file')
                else:
                    await bot.send_message(chat_id= message.from_user.id, text='wrong argument number')
            elif message.caption is None and message.text == 'enough':
                await bot.send_message(chat_id= message.from_user.id, text='back to edit. here is the command list (tbc) ...')
                #TODO: if directory is empty, attachments field in db set to false 
                await EditState.check.set()
        elif message.caption is None and message.document is not None:
                if not os.path.exists(f"storage/attachments/{edit_id}"):
                    os.makedirs(f"storage/attachments/{edit_id}")
                    await message.document.download(os.path.join(f'storage/attachments/{edit_id}', message.document.file_name))
                    await bot.send_message(chat_id= message.from_user.id, text='upload successful')
                else:
                    if message.document.file_name not in os.listdir(f'storage/attachments/{edit_id}'):
                        await message.document.download(os.path.join(f'storage/attachments/{edit_id}', message.document.file_name))
                        await bot.send_message(chat_id= message.from_user.id, text='upload successful')
                    else:
                         await bot.send_message(chat_id= message.from_user.id, text='file is already in directory')

            
if __name__ == '__main__':
    executor.start_polling(dp,skip_updates=True)
