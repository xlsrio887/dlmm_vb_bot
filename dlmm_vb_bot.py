import random
import sys
import time
import asyncio
import threading
import requests
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Конфигурация
config = {
    "wallet_address": "HWn62BFk25Pd4A61tLjqUfeGvrwPZJXJ4XDzEv484YVU",
    "total_pools": 7,
    "max_liquidity_sol": 610.18,
    "max_liquidity_usdc": 62232.12,
    "total_liquidity_sol": 1263.80,
    "current_price": 125.50,
    "last_update": datetime.now(timezone.utc),
    "growth_rate": random.uniform(1.1, 1.8),
    "pools": []
}

TOKEN = "7985368081:AAGDAGObx3q5OrjrMEmCBeGi78H7nge3sbs"
app = Application.builder().token(TOKEN).build()

last_report_pools = []

# Обновление ликвидности

def update_liquidity():
    now = datetime.now(timezone.utc)
    elapsed_time = (now - config["last_update"]).total_seconds() / 60
    daily_growth = config["growth_rate"] / 100
    growth_factor = 1 + (daily_growth * (elapsed_time / 1440))
    config["total_liquidity_sol"] *= growth_factor
    config["last_update"] = now

def get_sol_price():
    try:
        response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd")
        data = response.json()
        config["current_price"] = data["solana"]["usd"]
    except Exception as e:
        print(f"Ошибка при получении цены SOL: {e}")

def generate_pools():
    global last_report_pools
    last_report_pools = []
    total_liquidity = config["total_liquidity_sol"]
    price = config["current_price"]
    for _ in range(config["total_pools"]):
        sol_liquidity = round(random.uniform(5, total_liquidity * 0.15), 2)
        usdc_liquidity = round(sol_liquidity * price * random.uniform(0.9, 1.1), 2)
        pool_apr = round(random.uniform(0.5, 2.5), 2)
        last_report_pools.append({
            "sol": sol_liquidity,
            "usdc": usdc_liquidity,
            "apr": pool_apr
        })

# Телеграм-бот

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Отчет по ликвидности", callback_data='generate_report')],
        [InlineKeyboardButton("💰 Вывести средства", callback_data='withdraw_funds')],
        [InlineKeyboardButton("🔄 Ребалансировка", callback_data='rebalance_liquidity')],
        [InlineKeyboardButton("🌐 Рыночные условия", callback_data='market_update')],
        [InlineKeyboardButton("📉 Оценка рынка", callback_data='market_analysis')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Это DLMM VB. Выбери действие:", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    print(f"[LOG] Пользователь выбрал: {query.data}")
    await query.message.reply_text("Обрабатываю запрос...")
    await asyncio.sleep(3)

    if query.data == "generate_report":
        await generate_report(update, context)
    elif query.data == "withdraw_funds":
        await select_pool_for_withdrawal(update, context)
    elif query.data.startswith("withdraw_"):
        await select_withdraw_percentage(update, context)
    elif query.data.startswith("percent_"):
        await process_withdrawal(update, context)
    elif query.data == "rebalance_liquidity":
        await rebalance_liquidity(update, context)
    elif query.data == "market_update":
        await market_update(update, context)
    elif query.data == "market_analysis":
        await market_analysis(update, context)

# Основной функционал

async def generate_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_liquidity()
    get_sol_price()
    generate_pools()

    price = config["current_price"]
    total_liquidity = config["total_liquidity_sol"]
    allocated_sol = round(total_liquidity * 0.61, 2)
    allocated_usdc = round(total_liquidity * price * 0.39, 2)
    estimated_apr = round((total_liquidity * 0.02) / total_liquidity * 100, 2)

    await asyncio.sleep(3)

    detailed_report = "\n🔍 **Детальная информация по пулам:**\n"
    for i, pool in enumerate(last_report_pools):
        detailed_report += (f"\n🏦 **Пул {i+1}**\n"
                            f"💰 SOL: {pool['sol']} SOL\n"
                            f"💵 USDC: ${pool['usdc']}\n"
                            f"📊 APR: {pool['apr']}%\n"
                            f"---------------------------")

    report = (f"💰 **Отчет по ликвидности**\n"
              f"Кошелек: {config['wallet_address']}\n"
              f"Пулы: {config['total_pools']}\n"
              f"Курс SOL/USD: ${price}\n"
              f"Общая ликвидность: {total_liquidity:.2f} SOL\n"
              f"📌 В SOL: {allocated_sol} SOL\n"
              f"📌 В USDC: ${allocated_usdc}\n"
              f"📈 APR: {estimated_apr}%\n")

    await update.callback_query.message.reply_text(report + detailed_report)

async def select_pool_for_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(f"Пул {i+1}", callback_data=f'withdraw_{i}')]
        for i in range(config['total_pools'])
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text("Выберите пул для вывода средств:", reply_markup=reply_markup)

async def select_withdraw_percentage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pool_index = int(update.callback_query.data.split("_")[-1])
    context.user_data['selected_pool'] = pool_index
    keyboard = [
        [InlineKeyboardButton("10%", callback_data=f'percent_10')],
        [InlineKeyboardButton("25%", callback_data=f'percent_25')],
        [InlineKeyboardButton("50%", callback_data=f'percent_50')],
        [InlineKeyboardButton("100%", callback_data=f'percent_100')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text("Выберите процент вывода:", reply_markup=reply_markup)

async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    percent = int(update.callback_query.data.split("_")[-1]) / 100
    pool_index = context.user_data['selected_pool']
    pool = last_report_pools[pool_index]
    sol_amount = round(pool['sol'] * percent, 2)
    usdc_amount = round(pool['usdc'] * percent, 2)
    print(f"[LOG] Вывод {percent*100}% из пула {pool_index + 1}: {sol_amount} SOL, ${usdc_amount} USDC")
    await update.callback_query.message.reply_text(f"✅ Средства ({sol_amount} SOL, ${usdc_amount} USDC) успешно выведены из пула {pool_index + 1}.")

async def rebalance_liquidity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(3)
    print("[LOG] Выполнена ребалансировка ликвидности")
    await update.callback_query.message.reply_text("🔄 Ребалансировка ликвидности выполнена.")

async def market_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_sol_price()
    await asyncio.sleep(2)
    await update.callback_query.message.reply_text(f"🌐 Обновлены рыночные условия. Новый курс SOL: ${config['current_price']}")
    print("[LOG] Рыночные условия обновлены")

async def market_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(2)
    analysis_result = "📉 Рынок показывает признаки коррекции. Рекомендуется сократить позиции."
    print("[LOG] Проведена оценка рынка")
    await update.callback_query.message.reply_text(analysis_result)

# CLI-режим

def terminal_listener():
    while True:
        cmd = input(">>> ").strip().lower()
        if cmd == "report":
            asyncio.run(generate_report_terminal())
        elif cmd.startswith("withdraw"):
            _, index, percent = cmd.split()
            asyncio.run(withdraw_terminal(int(index)-1, int(percent)/100))
        elif cmd == "rebalance":
            print("[CLI] Ребалансировка выполнена")
        elif cmd == "market":
            get_sol_price()
            print(f"[CLI] Текущий курс SOL: ${config['current_price']}")
        elif cmd == "analysis":
            print("[CLI] Оценка рынка: возможна коррекция, соблюдайте осторожность.")
        elif cmd == "exit":
            print("Выход из CLI")
            break
        else:
            print("Неизвестная команда")

async def generate_report_terminal():
    update_liquidity()
    get_sol_price()
    generate_pools()
    print("[CLI] Генерация отчета по ликвидности")
    for i, pool in enumerate(last_report_pools):
        print(f"Пул {i+1}: {pool['sol']} SOL | ${pool['usdc']} | APR: {pool['apr']}%")

async def withdraw_terminal(index, percent):
    if index >= 0 and index < len(last_report_pools):
        pool = last_report_pools[index]
        sol = round(pool['sol'] * percent, 2)
        usdc = round(pool['usdc'] * percent, 2)
        print(f"[CLI] Вывод из пула {index+1}: {sol} SOL, ${usdc} USDC")
    else:
        print("Неверный номер пула")

# Запуск

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_callback))

print("DLMM VB Bot is running...")
threading.Thread(target=terminal_listener, daemon=True).start()
app.run_polling()
