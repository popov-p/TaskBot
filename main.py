import os, shutil
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
from datetime import date, datetime, timedelta
import re
import random
import asyncio, aioschedule
API_TOKEN = '6065585416:AAGyFxzNhsekSrFWfjaC3ubj8hzHDIaHKrc'

#logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

db.create_tables([Task])

async def check():
    to_notify = Task.select().where((Task.date == date.today()) & (Task.time < datetime.now().strftime(time_format)) & (Task.is_finished == False) & (Task.user_notified == False))
    for task in to_notify:
        print(str(task.user_id) + ' id user')
        chat = await bot.get_chat(task.user_id)
        state = dp.current_state(chat = chat.id)
        if await state.get_state() is None:
            print(f'time: {task.time}, now {datetime.now().strftime(time_format)}')
            await bot.send_message(chat_id=task.user_id, text=f'notification: \n' \
                                                            f'header:{task.header} \n' \
                                                                f'description: {task.description} \n '\
                                                                f'date: {task.date} \n'\
                                                                f'time: {task.time} \n '\
                                                                f'is periodic: {task.is_periodic} \n ')
            if(task.is_periodic):
                Task.create(user_id = task.user_id,
                            header = task.header + str(random.randint(1,100)),
                            description = task.description,
                            date = task.date + timedelta(task.interval),
                            time = task.time,
                            attachments = task.attachments,
                            is_periodic = task.is_periodic,
                            interval = task.interval,
                            is_finished = False)
            task.user_notified = True
            task.save()
            if task.attachments:
                for filename in os.scandir(f'storage/attachments/{task.id}'):
                    if filename.is_file():
                        with open(filename.path, 'rb') as file:
                            await bot.send_document(task.user_id, file)
        else:
            print('pass') 
            pass

async def scheduler():
    aioschedule.every(5).seconds.do(check)
    while True:
        await asyncio.gather(*[job.run() for job in aioschedule.jobs])
        await asyncio.sleep(1)

async def on_startup(_):
    asyncio.create_task(scheduler())

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
        return await bot.send_message(chat_id= message.from_user.id, text='there is no current tasks', reply_markup=start_kb)
    else:
        for row in query:
            await bot.send_message(chat_id= message.from_user.id, text=f'header: {str(row.header)} \n description: {str(row.description)} \n date: {str(row.date)}')
    await bot.send_message(chat_id=message.from_user.id, text=f'to edit write "edit <header> <option>" \n'\
                                                              f'to finish  write finish <header> \n'\
                                                              f'to delete write delete <header> \n', reply_markup=cancel_kb)
    await EditState.check.set()

@dp.message_handler(Text(equals='show finished tasks'), state=None)
async def show_finished_tasks(message: types.Message):
    query = Task.select().where(Task.is_finished == True)
    if len(query) == 0:
        return await message.reply('there are no finished tasks')
    else:
        for row in query:
            await bot.send_message(chat_id= message.from_user.id, text=f'header: {str(row.header)} \n description: {str(row.description)} \n date: {str(row.date)} \n time {str(row.time)}')
    await bot.send_message(chat_id= message.from_user.id, text='to get task back to current, write "unfinish <header> <date> <time>')
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
        await message.answer('state cancelled',reply_markup=start_kb)

@dp.message_handler(filters.Text(startswith='delete '), content_types = types.ContentTypes.TEXT, state=EditState.check)
async def delete_task(message: types.Message):
    options_list = message.text.split()
    tasks = Task.select().where(Task.header == options_list[1])
    if len(options_list) == 2:
        if len(tasks) != 0:
            try:
                Task.delete().where(Task.header == options_list[1]).execute()
                shutil.rmtree(f'storage/attachments/{tasks[0].id}')
            except Exception as e:
                print(type(e).__name__, e)
            await bot.send_message(chat_id= message.from_user.id, text=f'delete successful!')
        else:
            return await bot.send_message(chat_id= message.from_user.id, text=f'there is no such task to delete')
    else:
        await bot.send_message(chat_id= message.from_user.id, text=f'input correct command (delete)') 



@dp.message_handler(filters.Text(startswith='finish '), content_types = types.ContentTypes.TEXT, state=EditState.check)
async def handle_finish_task(message:types.Message):
    options_list = message.text.split()
    tasks = Task.select().where(Task.header == options_list[1])
    if len(options_list) == 2:
        if len(tasks) != 0:
            Task.update(is_finished = True).where(Task.header == options_list[1]).execute()
            await bot.send_message(chat_id= message.from_user.id, text=f'task finished!')
        else:
            await bot.send_message(chat_id= message.from_user.id, text=f'no such task to finish')
    else:
        await bot.send_message(chat_id= message.from_user.id, text=f'input correct command (finish)') 


@dp.message_handler(filters.Text(startswith='unfinish '), content_types = types.ContentTypes.TEXT, state=EditState.check)
async def handle_finish_task(message:types.Message, state=EditState.check):
    options_list = message.text.split()
    tasks = Task.select().where(Task.header == options_list[1], Task.is_finished == True)
    
    if len(options_list) == 4:
        if len(tasks) != 0:
            if(bool(re.match(r'(\d{4}-\d{2}-\d{2})', options_list[2]))  and bool(re.match(r'(\d{2}:\d{2}:\d{2})', options_list[3]))):
                Task.update(is_finished = False, user_notified = False, date = options_list[2], time = options_list[3]).where(Task.header == options_list[1]).execute()
                await bot.send_message(chat_id= message.from_user.id, text=f'update successful!')
            else:
                await bot.send_message(chat_id= message.from_user.id, text=f'wrong date or time')
        else:
            await bot.send_message(chat_id= message.from_user.id, text=f'no such task to unfinish')
    else:
        await bot.send_message(chat_id= message.from_user.id, text=f'input correct command (unfinish)')


@dp.message_handler(filters.Text(startswith='edit '), content_types = types.ContentTypes.TEXT, state=EditState.check)
async def handle_edit_task(message:types.Message, state:FSMContext):
    data = await state.get_data()
    options_list = message.text.split()
    tasks = Task.select().where(Task.header == options_list[1])
    #if wrong fix len tasks options list order
    if len(options_list) == 3:
        if len(tasks) != 0:
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
            elif options_list[2] == 'period':
                await message.reply('to make task periodic, write makeperiodic d HH:MM:SS \n to make task nonperiodic, write \n makenonperiodic ')
                await EditState.periodic.set()
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
            await message.reply('there is no such task')
    else:
        await message.reply('input correct command (edit)')

@dp.message_handler(content_types = types.ContentTypes.ANY, state=EditState.check)
async def edit_data(message: types.Message, state:FSMContext):
    await message.reply(f'to edit write "edit <header> <option>" \n'\
                        f'to finish  write finish <header> \n'\
                        f'to delete write delete <header> \n'
                        f'options are: description, date,time, attachments, period')



@dp.message_handler(content_types = types.ContentTypes.ANY, state=None)
async def handle_wrong_msg(message: types.Message):
    await message.reply('input correct command')

@dp.message_handler(content_types=types.ContentTypes.TEXT, state=TaskState.header)
async def header_check_save(message: types.Message, state: FSMContext):
    tasks = None
    divided_msg = message.text.split()
    if len(divided_msg) > 1 :
        return await bot.send_message(chat_id= message.from_user.id, text=f'header must be a one-word key')
    else:
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
            date = datetime.strptime(message.text, date_format).date()
        except ValueError:
            await message.reply('date format must be YYYY-MM-DD')
        if date < datetime.today().date():
            return await bot.send_message(chat_id= message.from_user.id, text='input correct date that is geq today')
        else:
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
            time = datetime.strptime(message.text, time_format).time()
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



@dp.message_handler(filters.Text(startswith='makeperiodic '), content_types = types.ContentTypes.TEXT, state=EditState.periodic)
async def makeperiodic_edit(message: types.Message, state: FSMContext):
    data = await state.get_data()
    options_list = message.text.split()
    if(len(options_list) == 3):
        if(bool(re.match(r'(\d+)', options_list[1]))  and bool(re.match(r'(\d{2}:\d{2}:\d{2})', options_list[2]))):
            task = Task.select().where(Task.id == data['edit_id'])
            try:
                Task.update(is_periodic = True, interval = options_list[1], time = options_list[2]).where(Task.id == data['edit_id']).execute()
                await bot.send_message(chat_id= message.from_user.id, text='ok.changes accepted!')
                return await EditState.check.set()
            except Exception as e:
                print(type(e).__name__, e)
                await bot.send_message(chat_id= message.from_user.id, text='smth went wrong (err periodic)')
        else:
            await bot.send_message(chat_id= message.from_user.id, text='argument error ()')
    else:
        await bot.send_message(chat_id= message.from_user.id, text='wrong param num (err periodic)')
@dp.message_handler(filters.Text(equals='makenonperiodic'), content_types = types.ContentTypes.TEXT, state=EditState.periodic)
async def makenonperiodic_edit(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        Task.update(is_periodic = False).where(Task.id == data['edit_id']).execute()
        await bot.send_message(chat_id= message.from_user.id, text='ok.changes accepted!(nonper)')
        return await EditState.check.set()
    except Exception as e: 
        print(type(e).__name__, e)
        await bot.send_message(chat_id= message.from_user.id, text='smth went wrong (err nonper)')


@dp.message_handler(content_types = types.ContentTypes.ANY, state=EditState.periodic)
async def period_handle_any(message: types.Message, state:FSMContext):
    await bot.send_message(chat_id= message.from_user.id, text='error: input a correct command (any)')


@dp.message_handler(filters.Text(equals='no'), content_types = types.ContentTypes.TEXT, state=TaskState.attachments)
async def no_attach(message: types.Message, state: FSMContext):
    data = await state.get_data()
    task = None
    if 'attachments' not in data:
        try:
            task = Task.create(user_id=message.from_user.id, header=data['header'], description=data['description'],
                        date=data['date'], time=data['time'], is_periodic = data['is_periodic'], interval = data['interval'],
                        is_finished = False)
        except Exception as e:
            print(type(e).__name__, e)
        await state.finish()
        await bot.send_message(chat_id= message.from_user.id, text='ok. task registered !', reply_markup=start_kb)
    else:
       await message.reply('text is not accepted. send files only')

@dp.message_handler(filters.Text(equals='yes'), content_types = types.ContentTypes.TEXT, state=TaskState.attachments)
async def yes_attach(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if 'attachments' not in data:
        async with state.proxy() as data:
            data['attachments'] = True
        await message.reply('load your files')
    else:
        await message.reply('text is not accepted. send files only')

@dp.message_handler(filters.Text(equals='enough'), content_types = types.ContentTypes.TEXT, state=TaskState.attachments)
async def enough_attach(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data.get('attachments'):
        if 'id' not in data:
            await message.reply('send at least one attachment to continue')
        else:
            await message.reply('ok. task registered !')
            await state.finish()
    else:
        await message.reply('need to add attachments [yes/no] ? (enough)')

@dp.message_handler(content_types=types.ContentTypes.TEXT, state=TaskState.attachments)
async def no_text_accepted(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data.get('attachments'):
        await message.reply('text is not accepted. send files only')
    else:
        await message.reply('need to add attachments [yes/no] ? (notext)')

@dp.message_handler(content_types=types.ContentTypes.ANY, state=TaskState.attachments)
async def load_files(message: types.Message, state: FSMContext):
    data = await state.get_data()
    task = None
    if data.get('attachments'):
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
                if not os.path.isdir(f"storage/attachments/{data['id']}"):
                    os.makedirs(f"storage/attachments/{data['id']}")
                notification_id = data['id']
                await message.document.download(os.path.join(f'storage/attachments/{notification_id}', message.document.file_name))
                await message.reply('doc loaded (later). if there`s no files more, press "enough"')
            else:
                task = Task.get_by_id(data['id'])
                notification_id = data['id']
                await message.document.download(os.path.join(f'storage/attachments/{notification_id}', message.document.file_name))
                await message.reply('doc loaded (later). if there`s no files more, press "enough"')
        else:
            await message.reply('send files only')
    else:
        await message.reply('need to add attachments [yes/no] ?') 


@dp.message_handler(filters.Text(startswith='delete all'), content_types = types.ContentTypes.TEXT, state=EditState.attachments)
async def delete_all_handler(message: types.Message, state:FSMContext):
    data = await state.get_data()
    edit_id = data['edit_id']
    try:
        if len(os.listdir(f'storage/attachments/{edit_id}')) == 0:
            return await bot.send_message(chat_id= message.from_user.id, text='nothing to delete. add files by drag`n`drop')
        else:
            for file in os.listdir(f'storage/attachments/{edit_id}'):
                try:
                    if os.path.isfile(os.path.join(f'storage/attachments/{edit_id}', file)):
                        os.remove(os.path.join(f'storage/attachments/{edit_id}', file))
                except Exception as e:
                    print(type(e).__name__+ ' inner', e)
            await bot.send_message(chat_id= message.from_user.id, text='delete successful')            
    except Exception as e:
        print(type(e).__name__ + ' outer', e)
        await bot.send_message(chat_id= message.from_user.id, text='nothing to delete. add files by drag`n`drop')

@dp.message_handler(filters.Text(startswith='delete '), content_types = types.ContentTypes.TEXT, state=EditState.attachments)
async def delete_file_handler(message:types.Message, state:FSMContext):
    data = await state.get_data()
    edit_id = data['edit_id']
    options_list = message.text.split()
    if len(options_list) == 2:
        file_to_del = options_list[1]
        try:
            if len(os.listdir(f'storage/attachments/{edit_id}')) == 0:
                return await bot.send_message(chat_id= message.from_user.id, text='nothing to delete. add files by drag`n`drop')
            os.remove(os.path.join(f'storage/attachments/{edit_id}', file_to_del))
            return await bot.send_message(chat_id= message.from_user.id, text='delete successful')
        except Exception as e:
            print(type(e).__name__, e)
            await bot.send_message(chat_id= message.from_user.id, text='there is no such file')
    else:
        await bot.send_message(chat_id= message.from_user.id, text='wrong argument number')  

@dp.message_handler(filters.Text(equals='enough'), content_types = types.ContentTypes.TEXT, state=EditState.attachments)
async def enough_edit_attach_handler(message:types.Message, state:FSMContext):
    data = await state.get_data()
    edit_id = data['edit_id']
    await bot.send_message(chat_id= message.from_user.id, text='back to edit. here is the command list (tbc) ...')
    if len(os.listdir(f'storage/attachments/{edit_id}')) == 0:
        Task.update(attachments = False).where(Task.id == data['edit_id']).execute()
    else:
        Task.update(attachments = True).where(Task.id == data['edit_id']).execute()
    await EditState.check.set()

@dp.message_handler(content_types=types.ContentTypes.ANY, state= EditState.attachments)
async def edit_load_file(message:types.Message, state:FSMContext):
    print('reached two files')
    data = await state.get_data()
    edit_id = data['edit_id']
    if message.caption is None and message.document is not None:
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
    elif message.text is not None:
        await bot.send_message(chat_id= message.from_user.id, text='wrong command (cmd)')
    else:
        await bot.send_message(chat_id= message.from_user.id, text='send only command or only file')


if __name__ == '__main__':
    executor.start_polling(dp,skip_updates=True, on_startup=on_startup)
