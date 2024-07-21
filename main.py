import os
import json
import logging
import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler, CallbackQueryHandler
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
creds_json = os.getenv("GOOGLE_SHEETS_CREDS_JSON")
creds_dict = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(os.getenv("GOOGLE_SHEET_ID")).sheet1

# Bot states
ALLERGY_SCORE, SYMPTOMS, MEDICATION, ACTIVITIES, NOTES = range(5)

async def start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Let's log your allergy data for today.")
    return await allergy_score(update, context)

async def allergy_score(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [InlineKeyboardButton(str(i), callback_data=f'score_{i}') for i in range(0, 6)],
        [InlineKeyboardButton(str(i), callback_data=f'score_{i}') for i in range(6, 11)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    context.user_data['current_score'] = 'sleep'
    await update.message.reply_text("Rate your Sleep allergy severity (1-10):", reply_markup=reply_markup)
    return ALLERGY_SCORE

async def process_allergy_score(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    
    score = int(query.data.split('_')[1])
    current_score = context.user_data['current_score']
    context.user_data[f'{current_score}_score'] = score
    
    if current_score == 'sleep':
        context.user_data['current_score'] = 'morning'
        await query.edit_message_text("Rate your Morning allergy severity (1-10):", reply_markup=query.message.reply_markup)
        return ALLERGY_SCORE
    elif current_score == 'morning':
        context.user_data['current_score'] = 'afternoon'
        await query.edit_message_text("Rate your Afternoon allergy severity (1-10):", reply_markup=query.message.reply_markup)
        return ALLERGY_SCORE
    elif current_score == 'afternoon':
        context.user_data['current_score'] = 'evening'
        await query.edit_message_text("Rate your Evening allergy severity (1-10):", reply_markup=query.message.reply_markup)
        return ALLERGY_SCORE
    else:
        await query.edit_message_text("Allergy scores logged successfully!")
        return await symptoms(update, context)

async def symptoms(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()

    selected_symptoms = context.user_data.get('symptoms', [])
    selected_text = f"Selected symptoms: {', '.join(selected_symptoms)}" if selected_symptoms else "No symptoms selected yet."

    keyboard = [
        [InlineKeyboardButton("Sneezing", callback_data='symptom_sneezing')],
        [InlineKeyboardButton("Runny nose", callback_data='symptom_runny_nose')],
        [InlineKeyboardButton("Itchy eyes", callback_data='symptom_itchy_eyes')],
        [InlineKeyboardButton("Congestion", callback_data='symptom_congestion')],
        [InlineKeyboardButton("Itchy throat", callback_data='symptom_itchy_throat')],
        [InlineKeyboardButton("Other (please specify)", callback_data='symptom_other')],
        [InlineKeyboardButton("Done", callback_data='symptom_done')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(f"Select your symptoms (press 'Done' when finished):\n{selected_text}", reply_markup=reply_markup)
    return SYMPTOMS

async def process_symptoms(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    
    symptom = '_'.join(query.data.split('_')[1:])
    if symptom == 'done':
        return await medication(update, context)

    if 'symptoms' not in context.user_data:
        context.user_data['symptoms'] = []

    if symptom in context.user_data['symptoms']:
        context.user_data['symptoms'].remove(symptom)
    else:
        context.user_data['symptoms'].append(symptom)

    return await symptoms(update, context)

async def medication(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data='medication_yes')],
        [InlineKeyboardButton("No", callback_data='medication_no')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Did you take any medication?", reply_markup=reply_markup)
    return MEDICATION

async def process_medication(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    
    medication = '_'.join(query.data.split('_')[1:])
    context.user_data['medication'] = medication
    
    return await activities(update, context)

async def activities(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    
    selected_activities = context.user_data.get('activities', [])
    selected_text = f"Selected activities: {', '.join(selected_activities)}" if selected_activities else "No activities selected yet."

    keyboard = [
        [InlineKeyboardButton("Stayed indoors", callback_data='activity_indoors')],
        [InlineKeyboardButton("Went outside", callback_data='activity_outside')],
        [InlineKeyboardButton("Used air purifier", callback_data='activity_purifier')],
        [InlineKeyboardButton("Took steam", callback_data='activity_steam')],
        [InlineKeyboardButton("Drank hot water", callback_data='activity_hot_water')],
        [InlineKeyboardButton("Took Ayurvedic medicine", callback_data='activity_ayurvedic')],
        [InlineKeyboardButton("Other (please specify)", callback_data='activity_other')],
        [InlineKeyboardButton("Done", callback_data='activity_done')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(f"Select relevant factors (press 'Done' when finished):\n{selected_text}", reply_markup=reply_markup)
    return ACTIVITIES

async def process_activities(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    
    activity = '_'.join(query.data.split('_')[1:])
    if activity == 'done':
        return await notes(update, context)
    
    if 'activities' not in context.user_data:
        context.user_data['activities'] = []

    if activity in context.user_data['activities']:
        context.user_data['activities'].remove(activity)
    else:
        context.user_data['activities'].append(activity)

    return await activities(update, context)

async def notes(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Please enter any additional notes for today:")
    return NOTES

async def process_notes(update: Update, context: CallbackContext) -> int:
    context.user_data['notes'] = update.message.text
    await update.message.reply_text("Notes saved successfully!")
    
    # Log all collected data to sheets
    log_to_sheets(context.user_data)
    
    await update.message.reply_text("All data has been logged. Thank you!")
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text('Bye! Your input has been canceled.')
    return ConversationHandler.END

async def send_reminder(context: CallbackContext):
    job = context.job
    await context.bot.send_message(job.context, text="Don't forget to log your allergy data for today!")

def schedule_reminder(application: Application):
    application.job_queue.run_daily(
        send_reminder, 
        time=datetime.time(hour=22, minute=0, tzinfo=pytz.timezone('Asia/Kolkata')),
        chat_id=7396293228  # Replace with the actual chat ID
    )

def log_to_sheets(data):
    # e.g. {'current_score': 'evening', 'sleep_score': 5, 'morning_score': 4, 'afternoon_score': 3, 'evening_score': 2, 'symptoms': ['itchy'], 'medication': 'no', 'activities': ['indoors'], 'notes': 'none'}
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [
        now,
        data.get('sleep_score', ''),
        data.get('morning_score', ''),
        data.get('afternoon_score', ''),
        data.get('evening_score', ''),
        ', '.join(data.get('symptoms', [])),
        data.get('medication', ''),
        ', '.join(data.get('activities', [])),
        data.get('notes', '')
    ]
    try:
        sheet.append_row(row)
        logger.info("Data successfully logged to Google Sheets")
    except Exception as e:
        logger.error(f"Error logging data to Google Sheets: {e}")

def main() -> None:
    application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ALLERGY_SCORE: [CallbackQueryHandler(process_allergy_score, pattern='^score_')],
            SYMPTOMS: [CallbackQueryHandler(process_symptoms, pattern='^symptom_')],
            MEDICATION: [CallbackQueryHandler(process_medication, pattern='^medication_')],
            ACTIVITIES: [CallbackQueryHandler(process_activities, pattern='^activity_')],
            NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_notes)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    schedule_reminder(application)
    application.run_polling()

if __name__ == '__main__':
    main()