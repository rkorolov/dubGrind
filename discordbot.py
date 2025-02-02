# discordbot.py
import discord
from discord.ext import commands, tasks
import asyncio
import openai  # Import OpenAI for API usage
import os # for key usage
from dotenv import load_dotenv # for key usage pt2
from pdf_summarize import summarize_file # for summarizing pdfs
from chatbotmodule import generate_quiz # for quiz generation
from study_guide_generator import generate_study_guide # for study guide generation
from discord import Embed


from husky import get_user_husky, user_huskies

# Bot setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="~", intents=intents, help_command=None)

#file uploads
if not os.path.exists('uploads'):
    os.makedirs('uploads')

#TODO: Section commands by category
    

#GENERATORS
    

# @bot.command()
@commands.command()
async def summarize(ctx):
    '''
    Summarizes a given PDF file.
    '''
    await ctx.send("📎 Please upload a PDF file within 30 seconds.")

    try:
        # Wait for the user's message with an attachment
        message = await bot.wait_for(
            "message",
            timeout=30,  # Timeout in seconds
            check=lambda m: m.author == ctx.author and m.attachments
        )

        # Check if the attachment is a PDF
        attachment = message.attachments[0]
        if attachment.filename.endswith('.pdf'):
            file_path = os.path.join('uploads', attachment.filename)
            await attachment.save(file_path)

            await ctx.send(f"✅ PDF `{attachment.filename}` has been uploaded successfully!")
            
            await ctx.send(f"🌀 Generating summary ...")

            # Summarize the PDF file
            summary = summarize_file(file_path)

            await ctx.send(summary.strip())
            
        else:
            await ctx.send("⚠️ Please upload a valid PDF file.")

    except asyncio.TimeoutError:
        await ctx.send("⏰ You took too long to upload the file. Please try again.")

# AI Question Generation

async def generate_ai_questions(num_questions):
    questions = {}
    for i in range(1, num_questions + 1):
        # Use OpenAI to generate a multiple-choice question
        prompt = (
            "Generate a multiple-choice question on a general topic. Include four answer options and indicate the correct answer."
        )
        try:
            response = openai.Completion.create(
                engine="text-davinci-003",  # Adjust the engine as needed
                prompt=prompt,
                max_tokens=150,
                temperature=0.7,
            )
            ai_output = response.choices[0].text.strip()

            # Parse the response into question and answers
            lines = ai_output.split("\n")
            question = lines[0]
            answers = [line for line in lines[1:5]]  # Extract the four answers
            correct_index = next(
                (i for i, ans in enumerate(answers) if "(correct)" in ans), None
            )

            if correct_index is not None:
                correct_index = correct_index
                answers = [ans.replace("(correct)", "").strip() for ans in answers]
                questions[i] = {
                    "question": question,
                    "answers": answers,
                    "correct": correct_index,
                }
            else:
                # Skip the question if no correct answer is found
                continue

        except Exception as e:
            print(f"Error generating question {i}: {e}")
            continue

    return questions


# Command to run an AI-powered quiz
# @bot.command() --> new version with backend is below
async def ai_quiz(ctx, num_questions: int):
    if num_questions <= 0 or num_questions > 50:
        await ctx.send("Please choose a number between 1 and 50.")
        return

    await ctx.send(f"Generating {num_questions} questions using AI. Please wait...")

    try:
        ai_questions = await generate_ai_questions(num_questions)
        if not ai_questions:
            await ctx.send("Failed to generate questions. Please try again later.")
            return

        question_ids = list(ai_questions.keys())

        score = 0
        for question_id in question_ids:
            q_data = ai_questions[question_id]
            question_text = f"**Question {question_id}:** {q_data['question']}\n"
            for i, answer in enumerate(q_data["answers"]):
                question_text += f"{i + 1}. {answer}\n"
            await ctx.send(question_text)

            def check_answer(msg):
                return msg.author == ctx.author and msg.channel == ctx.channel and msg.content.isdigit()

            try:
                answer_msg = await bot.wait_for("message", check=check_answer, timeout=60)
                user_answer = int(answer_msg.content) - 1

                if user_answer == q_data["correct"]:
                    score += 1
                    await ctx.send("Correct!")
                else:
                    await ctx.send(f"Wrong! The correct answer was: {q_data['answers'][q_data['correct']]}")
            except Exception:
                await ctx.send("You took too long to answer. Moving to the next question.")

        await ctx.send(f"AI Quiz finished! You scored {score}/{num_questions}.")
    except Exception as e:
        await ctx.send(f"An error occurred while generating the quiz: {e}")

#linked backend pt1 -- WORKS !! :D #justachillguy
# @bot.command()
@commands.command()
async def gen_question(ctx):
    '''
    Generates a quiz based on a given topic and number of questions.
    '''
    quiz_content = await gen_question_helper(ctx)
    
    if not quiz_content:
        await ctx.send("Failed to generate quiz. Please try again later.")
        return
    
    score = 0
    total_questions = len(quiz_content)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.upper() in ['A', 'B', 'C', 'D']

    await ctx.send(f"🐋 **Quiz generated!** You have 20 seconds to answer each question. Type `A`, `B`, `C`, or `D` to respond.\n")


    for question, data in quiz_content.items():
        choices = data["choices"]
        correct_answer = data["correct"]

        # Format the question with choices (A, B, C, D)
        formatted_choices = "\n".join([f"{chr(65+i)}. {choice}" for i, choice in enumerate(choices)])
        await ctx.send(f"**{question}**\n{formatted_choices}")

        try:
            # Wait for the user's response
            msg = await bot.wait_for('message', timeout=20.0, check=check)
            user_answer = msg.content.upper()
            selected_choice = choices[ord(user_answer) - 65]  # Map A/B/C/D to choices list

            # Check if the answer is correct
            if selected_choice == correct_answer:
                await ctx.send("✅ Correct!\n")
                score += 1
            else:
                await ctx.send(f"❌ Incorrect! The correct answer was **{correct_answer}**.\n")

        except asyncio.TimeoutError:
            await ctx.send(f"⏰ Time's up! The correct answer was **{correct_answer}**.\n")

    # Final score
    await ctx.send(f"🎉 **Quiz Complete!** You scored **{score}/{total_questions}**!")

#linked backend pt2
async def gen_question_helper(ctx):
    await ctx.send("📝 How many questions would you like in the quiz? (e.g., 5)")

    def check_author(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    try:
        # Wait for the number of questions
        msg_num = await bot.wait_for('message', timeout=30.0, check=check_author)
        num_questions = int(msg_num.content)

        await ctx.send("🔍 What topic should the quiz be about?")

        # Wait for the topic
        msg_topic = await bot.wait_for('message', timeout=30.0, check=check_author)
        topic = msg_topic.content

        await ctx.send("Generating quiz ...")

        # Generate the quiz
        quiz_content = generate_quiz(topic, num_questions)

        # Send the quiz back to the user
        print(quiz_content)
        await ctx.send("Generated!")
        return quiz_content

    except asyncio.TimeoutError:
        await ctx.send("⏰ You took too long to respond. Please try again.")
    except ValueError:
        await ctx.send("⚠️ Please enter a valid number for the number of questions.")

def chunk_maker(text, limit=1024):
    """Splits text into chunks without cutting words."""
    chunks = []
    while len(text) > limit:
        # Find the last newline or period before the limit
        split_index = text.rfind("\n", 0, limit)
        if split_index == -1:
            split_index = text.rfind(".", 0, limit) + 1
        if split_index <= 0:
            split_index = limit  # Hard split if no good breakpoint

        chunks.append(text[:split_index].strip())
        text = text[split_index:].strip()

    chunks.append(text.strip())
    return chunks

async def study_guide_embed(ctx, study_guide):
    embed = Embed(title="📚 Study Guide", color=int('848ECB', 16))

    sections = study_guide.strip().split("---")  # Assuming "---" separates sections


    for idx, section in enumerate(sections, start=1):
        chunks = chunk_maker(section)

        for part_idx, chunk in enumerate(chunks):
            # title = f"Section {idx}" if part_idx == 0 else f"Section {idx} (cont.)"
            # embed.add_field(name=title, value=chunk, inline=False)
                
            embed.add_field(name="", value=chunk, inline=False)

    await ctx.send(embed=embed)

# @bot.command()
@commands.command()
async def gen_study_guide(ctx):
    '''
    Generates a study guide based on a given PDF file.
    '''
    await ctx.send("📎 Please upload a PDF file within 30 seconds.")

    try:
        # Wait for the user's message with an attachment
        message = await bot.wait_for(
            "message",
            timeout=30,  # Timeout in seconds
            check=lambda m: m.author == ctx.author and m.attachments
        )

        # Check if the attachment is a PDF
        attachment = message.attachments[0]
        if attachment.filename.endswith('.pdf'):
            file_path = os.path.join('uploads', attachment.filename)
            await attachment.save(file_path)

            await ctx.send(f"✅ PDF `{attachment.filename}` has been uploaded successfully!")

            await ctx.send(f"🌀 Generating study guide ...")

            # Generate the study guide

            study_guide = generate_study_guide(file_path)

            await study_guide_embed(ctx, study_guide) # split into sections to avoid character limit + yay formatting
            
        else:
            await ctx.send("⚠️ Please upload a valid PDF file.")

    except asyncio.TimeoutError:
        await ctx.send("⏰ You took too long to upload the file. Please try again.")


# Pomodoro Timer Command
@bot.command()
async def ptimer(ctx, work_time: int = 25, break_time: int = 5):
    """
    Starts a Pomodoro timer with a default 25-minute work session and a 5-minute break.
    """
    try:
        await ctx.send(f"Pomodoro timer started! Working for {work_time} minutes.")

        # Work timer
        await asyncio.sleep(work_time * 60)
        await ctx.send(f"Time's up! Take a {break_time}-minute break.")

        # Break timer
        await asyncio.sleep(break_time * 60)
        await ctx.send("Break's over! Time to get back to work!")
    except Exception as e:
        await ctx.send("An error occurred with the Pomodoro timer.")
        print(f"Error: {e}")

#manual add
bot.add_command(summarize)
bot.add_command(gen_study_guide)
bot.add_command(gen_question)

class CustomHelpCommand(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="📚 Bot Commands", color=0x848ECB)

        # Custom Categories
        categories = {
            "🛠️ Generating Commands": [summarize, gen_study_guide, gen_question],
            "Study Commands": [ptimer],
            
        }

        # Add commands to the embed
        for category, commands_list in categories.items():
            command_names = "\n".join(f"`{cmd.name}` - {cmd.help}" for cmd in commands_list)
            embed.add_field(name=category, value=command_names, inline=False)

        await self.get_destination().send(embed=embed)

# Apply the Custom Help Command
bot.help_command = CustomHelpCommand()

# Daily reset and stat decay
@tasks.loop(hours=24)
async def daily_reset():
    for user_id, husky in user_huskies.items():
        husky.decay()
        husky.reset_daily_study()
    print("Daily stats updated for all users (decay applied if goal not met).")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

    daily_reset.start()  # Start the daily reset loop

load_dotenv()
DISCORD_KEY = os.getenv("DISCORD_KEY")
if not DISCORD_KEY:
        raise ValueError("Please set the DISCORD_KEY environment variable")
# Run the bot
bot.run(DISCORD_KEY)

