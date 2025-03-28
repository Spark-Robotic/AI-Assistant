# AI Implementation Assistant
# 
# This application helps organizations implement specialized processes by:
# - Providing expert guidance on requirements through AI
# - Managing and enriching implementation tasks in Asana
# - Offering a Slack interface for team communication
# - Following a structured implementation approach defined in Path.txt

import os
import json
import time
import re
import asyncio
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv
import asana
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import queue
import signal
import sys
import requests
import argparse

# Load environment variables
load_dotenv()

# Check if .env file exists
if not os.path.exists('.env'):
    print("Warning: .env file not found in the current directory")
    print(f"Current working directory: {os.getcwd()}")
    print("Creating default .env file template...")
    
    with open('.env', 'w') as f:
        f.write("""# Slack credentials
SLACK_BOT_TOKEN=your-slack-bot-token
SLACK_APP_TOKEN=your-slack-app-token

# Asana credentials 
ASANA_TOKEN=your-asana-token
ASANA_PROJECT_ID=your-asana-project-id

# OpenAI API  
OPENAI_API_KEY=your-openai-api-key""")
    
    # Try loading again
    load_dotenv()

# Log successful environment loading
print("Environment variables loaded successfully")

# Configuration
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")  # xapp-... token
ASANA_TOKEN = os.getenv("ASANA_TOKEN")
ASANA_PROJECT_ID = os.getenv("ASANA_PROJECT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "AI Assistant")

# Fallback to hardcoded values if environment variables are not loaded
if not SLACK_BOT_TOKEN:
    print("Warning: SLACK_BOT_TOKEN not found in environment variables.")
    print("Please add SLACK_BOT_TOKEN to your .env file")
    sys.exit(1)

if not SLACK_APP_TOKEN:
    print("Warning: SLACK_APP_TOKEN not found in environment variables.")
    print("Please add SLACK_APP_TOKEN to your .env file")
    sys.exit(1)

# Fallback for Asana tokens
if not ASANA_TOKEN:
    print("Warning: ASANA_TOKEN not found in environment variables.")
    print("Please add ASANA_TOKEN to your .env file")
    sys.exit(1)

if not ASANA_PROJECT_ID:
    print("Warning: ASANA_PROJECT_ID not found in environment variables.")
    print("Please add ASANA_PROJECT_ID to your .env file")
    sys.exit(1)

if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not found in environment variables.")
    print("Please add OPENAI_API_KEY to your .env file")
    print("Some API-based features will not work")

# Initialize clients
asana_client = asana.Client.access_token(ASANA_TOKEN)
app = App(token=SLACK_BOT_TOKEN)

# Bot ID for mention detection
BOT_ID = None

# Get bot ID on startup
def get_bot_id():
    """Retrieve the bot's user ID from Slack"""
    try:
        global BOT_ID
        # Call auth.test to get our own user ID
        result = app.client.auth_test()
        BOT_ID = result["user_id"]
        print(f"Bot ID: {BOT_ID}")
        return BOT_ID
    except Exception as e:
        print(f"Error getting bot ID: {e}")
        return None

# Store conversation history for GPT
conversation_history = {}

# Load domain knowledge from Path.txt
DOMAIN_KNOWLEDGE = ""
try:
    with open("Path.txt", "r") as f:
        DOMAIN_KNOWLEDGE = f.read()
    print("Successfully loaded domain knowledge from Path.txt")
except Exception as e:
    print(f"Warning: Could not load Path.txt - {e}")
    print("The assistant will have limited domain-specific knowledge")
    DOMAIN_KNOWLEDGE = "No specific domain knowledge provided."

# Parse implementation phases from Path.txt
# Format expected: Phase headings as lines ending with "Week X-Y" or similar
IMPLEMENTATION_PHASES = {}
try:
    phase_pattern = re.compile(r"PHASE (\d+): (.*?)\s*\(([^)]+)\)")
    matches = phase_pattern.findall(DOMAIN_KNOWLEDGE)
    
    if matches:
        for phase_num, phase_name, timeline in matches:
            IMPLEMENTATION_PHASES[phase_num] = {
                "name": f"{phase_name} ({timeline})",
                "description": "",
                "key_activities": [],
                "deliverables": []
            }
        print(f"Found {len(IMPLEMENTATION_PHASES)} implementation phases in Path.txt")
    else:
        print("No phase information found in Path.txt")
except Exception as e:
    print(f"Error parsing phases: {e}")

#################################################
#            AI Assistant Class                 #
#################################################

class AIAssistant:
    """Domain-specific AI Assistant using OpenAI API"""
    
    def __init__(self, model="gpt-3.5-turbo"):
        """
        Initialize the AI Assistant with the specified AI model.
        
        Args:
            model (str): The OpenAI model to use for generating responses 
                        (default: "gpt-3.5-turbo")
        """
        self.model = model
        print(f"Initialized AI Assistant with model: {model}")
    
    def ask_question(self, question):
        """Ask a question to the AI expert"""
        try:
            print(f"Asking AI expert: {question}")
            
            # Prepare the prompt with domain context
            prompt = f"""You are an expert consultant on the specific processes described in the following context.
            
            CONTEXT FROM PATH.TXT:
            {DOMAIN_KNOWLEDGE[:3000]}... (abbreviated for prompt length)
            
            Please answer this question about implementing these processes:
            {question}
            
            Provide a comprehensive but practical answer based on the knowledge provided.
            Reference specific sections of the implementation path where relevant.
            """
            
            # Make the API request to OpenAI
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are an expert consultant providing guidance on implementation."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
            
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
            
            if response.status_code == 200:
                response_data = response.json()
                message = response_data['choices'][0]['message']['content'].strip()
                return message
            else:
                # Enhanced error handling with specific status code feedback
                if response.status_code == 401:
                    print(f"Authentication error: Check your OPENAI_API_KEY in .env file")
                elif response.status_code == 429:
                    print(f"Rate limit or quota exceeded: Check your OpenAI billing status")
                elif response.status_code == 500:
                    print(f"OpenAI server error, please try again later")
                else:
                    print(f"Error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"Exception in ask_question: {str(e)}")
            # More specific guidance for common errors
            if "Connection" in str(e):
                print("Network error: Check your internet connection")
            elif "SSLError" in str(e):
                print("SSL error: Check your network security settings")
            return None
    
    async def process_tasks(self, limit=None):
        """Process and enrich Asana tasks based on Path.txt knowledge"""
        try:
            print(f"Processing tasks from Asana project {ASANA_PROJECT_ID}")
            
            # Enrich task descriptions with domain knowledge
            self.enrich_task_descriptions(limit)
            
            # Get upcoming tasks
            upcoming_tasks = self.get_upcoming_tasks(7)  # Next 7 days
            
            if upcoming_tasks:
                print(f"Found {len(upcoming_tasks)} upcoming tasks")
                
                for task in upcoming_tasks:
                    print(f"- {task.get('name', 'Unnamed task')}")
            else:
                print("No upcoming tasks found")
                
        except Exception as e:
            print(f"Error processing tasks: {e}")
    
    def enrich_task_descriptions(self, limit=None):
        """Have the AI expert write detailed descriptions for each Asana task"""
        try:
            print("Enriching task descriptions with domain expertise...")
            
            # Load the implementation path for context
            path_content = ""
            try:
                with open("Path.txt", "r") as f:
                    path_content = f.read()
                print("Loaded implementation path for context")
            except Exception as e:
                print(f"Could not load Path.txt file: {e}")
            
            # Get all tasks from the project
            tasks = asana_client.tasks.get_tasks_for_project(
                ASANA_PROJECT_ID,
                {'opt_fields': 'name,notes,completed,gid'}
            )
            
            # Filter for incomplete tasks
            incomplete_tasks = [task for task in tasks if not task.get('completed', False)]
            
            if limit:
                tasks_to_process = incomplete_tasks[:limit]
            else:
                tasks_to_process = incomplete_tasks
            
            print(f"Found {len(tasks_to_process)} tasks to enrich")
            
            # Track results
            results = {
                'processed': 0,
                'updated': 0,
                'skipped': 0,
                'failed': 0
            }
            
            # Process each task
            for i, task in enumerate(tasks_to_process):
                try:
                    task_name = task.get('name', 'Unnamed task')
                    task_id = task.get('gid')
                    existing_notes = task.get('notes', '')
                    
                    print(f"\nEnriching task {i+1}/{len(tasks_to_process)}: {task_name}")
                    
                    # Skip if already has substantial notes
                    if len(existing_notes) > 200 and "TASK DESCRIPTION" in existing_notes:
                        print(f"Task already has detailed description. Skipping.")
                        results['skipped'] += 1
                        continue
                    
                    # Generate a description prompt specific to this task
                    prompt = f"""As an expert on the processes described in the implementation path, write a detailed description for the following task:
                    
                    TASK NAME: {task_name}
                    
                    IMPLEMENTATION CONTEXT:
                    {path_content[:1500]}... (abbreviated for prompt length)
                    
                    Your description should include:
                    1. The purpose and importance of this task in the implementation
                    2. Key requirements related to this task
                    3. Implementation guidance (how to complete this task effectively)
                    4. Common pitfalls to avoid
                    5. How this task connects to other parts of the system
                    6. How this task fits into the implementation path described above
                    
                    Format the description in clear paragraphs with appropriate headings.
                    """
                    
                    # Call the OpenAI API
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {OPENAI_API_KEY}"
                    }
                    
                    data = {
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are an expert consultant providing implementation guidance."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7
                    }
                    
                    print(f"Generating description for task: {task_name}")
                    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        description = response_data['choices'][0]['message']['content'].strip()
                        
                        # Format the description
                        formatted_description = f"""
# TASK DESCRIPTION
Generated by {ASSISTANT_NAME} on {datetime.now().strftime('%Y-%m-%d')}

{description}

---
Original task: {task_name}
                        """
                        
                        # Update the task in Asana
                        updated_notes = formatted_description if not existing_notes else f"{existing_notes}\n\n{formatted_description}"
                        
                        asana_client.tasks.update_task(task_id, {'notes': updated_notes})
                        print(f"✅ Updated task description for: {task_name}")
                        results['updated'] += 1
                    else:
                        print(f"❌ Failed to generate description: {response.status_code} - {response.text}")
                        results['failed'] += 1
                    
                    results['processed'] += 1
                    
                    # Small delay to avoid rate limits
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"Error processing task {task.get('name', 'Unknown')}: {e}")
                    results['failed'] += 1
            
            print("\n--- TASK ENRICHMENT SUMMARY ---")
            print(f"Processed: {results['processed']} tasks")
            print(f"Updated: {results['updated']} tasks")
            print(f"Skipped: {results['skipped']} tasks")
            print(f"Failed: {results['failed']} tasks")
            
        except Exception as e:
            print(f"Error in task enrichment: {e}")
    
    def get_upcoming_tasks(self, days=7):
        """Get upcoming tasks for the next X days"""
        try:
            today = datetime.now().date()
            target_date = (today + timedelta(days=days)).strftime('%Y-%m-%d')
            
            # Get tasks due in the next X days
            tasks = asana_client.tasks.get_tasks_for_project(
                ASANA_PROJECT_ID,
                {
                    'opt_fields': 'name,due_on,assignee.name,completed',
                    'due_on.before': target_date
                }
            )
            
            # Filter out completed tasks
            upcoming_tasks = [task for task in tasks if not task.get('completed', False)]
            
            return upcoming_tasks
        except Exception as e:
            print(f"Error getting upcoming tasks: {e}")
            return []
    
    def get_task_status(self):
        """Get tasks status for reporting"""
        try:
            # Get all tasks
            tasks = asana_client.tasks.get_tasks_for_project(
                ASANA_PROJECT_ID,
                {'opt_fields': 'name,completed,due_on,assignee.name'}
            )
            
            # Count tasks by status
            total = len(tasks)
            completed = sum(1 for task in tasks if task.get('completed', False))
            incomplete = total - completed
            
            # Count unassigned tasks
            unassigned = sum(1 for task in tasks if not task.get('completed', False) and not task.get('assignee'))
            
            # Count overdue tasks
            today = datetime.now().date().strftime('%Y-%m-%d')
            overdue = sum(1 for task in tasks if 
                not task.get('completed', False) and 
                task.get('due_on') and 
                task.get('due_on') < today
            )
            
            # Sort tasks by phase if we can extract that info
            phases = {}
            for task in tasks:
                name = task.get('name', '')
                
                # Try to extract phase number from task name
                for phase_num in IMPLEMENTATION_PHASES.keys():
                    if f"PHASE {phase_num}:" in name or name.startswith(f"PHASE {phase_num}:"):
                        if phase_num not in phases:
                            phases[phase_num] = {'total': 0, 'completed': 0}
                        
                        phases[phase_num]['total'] += 1
                        if task.get('completed', False):
                            phases[phase_num]['completed'] += 1
                        break
            
            # Calculate percentages for each phase
            for phase_num, data in phases.items():
                if data['total'] > 0:
                    data['percentage'] = round((data['completed'] / data['total']) * 100, 1)
                else:
                    data['percentage'] = 0
            
            # Calculate overall percentage
            percentage = round((completed / total) * 100, 1) if total > 0 else 0
            
            return {
                'total': total,
                'completed': completed,
                'incomplete': incomplete,
                'unassigned': unassigned,
                'overdue': overdue,
                'percentage': percentage,
                'phases': phases
            }
        except Exception as e:
            print(f"Error getting task status: {e}")
            return None
    
    def bulk_assign_tasks(self, tasks, assignee, due_on=None):
        """
        Assign multiple tasks to the same person with an optional due date.
        
        Args:
            tasks (list): List of task dictionaries containing 'gid' and 'name'
            assignee (str): Name of the person to assign tasks to
            due_on (str, optional): Due date in YYYY-MM-DD format
            
        Returns:
            dict: Results summary showing successful and failed assignments
        """
        results = {
            'success': 0,
            'failed': 0,
            'tasks': []
        }
        
        # Get all users to find the assignee
        users = list(asana_client.users.find_all())
        
        # Find the assignee's gid
        assignee_gid = None
        for user in users:
            if assignee.lower() in user['name'].lower():
                assignee_gid = user['gid']
                break
        
        if not assignee_gid:
            print(f"Could not find user: {assignee}")
            return results
        
        # Prepare update data
        update_data = {'assignee': assignee_gid}
        if due_on:
            update_data['due_on'] = due_on
        
        # Update each task
        for task in tasks:
            try:
                task_id = task['gid']
                asana_client.tasks.update_task(task_id, update_data)
                results['success'] += 1
                results['tasks'].append({
                    'id': task_id,
                    'name': task.get('name', 'Unknown task')
                })
                print(f"✅ Updated task: {task.get('name', task_id)}")
            except Exception as e:
                results['failed'] += 1
                results['tasks'].append({
                    'id': task.get('gid', 'Unknown'),
                    'name': task.get('name', 'Unknown task'),
                    'error': str(e)
                })
                print(f"❌ Failed to update task: {task.get('name', task_id)}")
        
        return results

#################################################
#             SLACK COMMANDS                    #
#################################################

# This is the main command handler for Slack
@app.command("/assistant")
def handle_assistant_command(ack, command, say):
    # Acknowledge command received
    ack()
    
    # Parse the command
    text = command['text']
    
    # Split into subcommand and content
    parts = text.strip().split(' ', 1)
    subcommand = parts[0].lower() if parts else ""
    content = parts[1] if len(parts) > 1 else ""
    
    # Get user who issued the command
    user_id = command['user_id']
    
    # Create an instance of the assistant
    assistant = AIAssistant()
    
    # Process different subcommands
    if subcommand == "help" or not subcommand:
        # Show help message
        show_help(say)
    
    elif subcommand == "ask":
        # Ask a question to the expert
        if not content:
            say("Please provide a question after 'ask'. For example: `/assistant ask What is the next step?`")
            return
        
        say(f"Asking the AI Assistant: *{content}*\nPlease wait...")
        
        # Get the response
        response = assistant.ask_question(content)
        
        if response:
            # Save the conversation context
            conversation_key = f"slack-{user_id}"
            if conversation_key not in conversation_history:
                conversation_history[conversation_key] = []
            
            # Add to conversation history
            conversation_history[conversation_key].append({
                "role": "user",
                "content": content
            })
            conversation_history[conversation_key].append({
                "role": "assistant", 
                "content": response
            })
            
            say(response)
        else:
            say("Sorry, I couldn't get an answer to that question. Please try rephrasing.")
    
    elif subcommand == "tasks":
        # Show upcoming tasks
        try:
            upcoming_tasks = assistant.get_upcoming_tasks()
            
            if not upcoming_tasks:
                say("No upcoming tasks found.")
                return
            
            # Format the response
            response = "*Upcoming Tasks:*\n"
            
            for task in upcoming_tasks:
                due_date = task.get('due_on', 'No due date')
                assignee = task.get('assignee', {}).get('name', 'Unassigned')
                
                response += f"• *{task.get('name')}*\n"
                response += f"  Due: {due_date} | Assignee: {assignee}\n"
            
            say(response)
        except Exception as e:
            say(f"Error retrieving tasks: {str(e)}")
    
    elif subcommand == "status":
        # Show implementation status
        status = assistant.get_task_status()
        
        if not status:
            say("Could not retrieve implementation status.")
            return
        
        # Format the response
        response = f"*Implementation Status*\n"
        response += f"Total Tasks: {status['total']}\n"
        response += f"Progress: {status['completed']}/{status['total']} tasks ({status['percentage']}%)\n"
        response += f"Incomplete: {status['incomplete']} tasks\n"
        response += f"Unassigned: {status['unassigned']} tasks\n"
        response += f"Overdue: {status['overdue']} tasks\n\n"
        
        # Add phase information if available
        if status['phases']:
            response += "*Progress by Phase:*\n"
            
            for phase_num, phase_data in sorted(status['phases'].items()):
                phase_name = IMPLEMENTATION_PHASES.get(phase_num, {}).get('name', f'Phase {phase_num}')
                response += f"• {phase_name}: {phase_data['completed']}/{phase_data['total']} ({phase_data['percentage']}%)\n"
        
        say(response)
    
    elif subcommand == "enrich":
        # Enrich task descriptions with AI
        try:
            # Get an optional limit
            limit = None
            if content.isdigit():
                limit = int(content)
            
            say(f"Starting task enrichment process{f' for {limit} tasks' if limit else ''}. This may take a few minutes...")
            
            # Start the enrichment in a separate thread to not block
            def run_enrichment():
                try:
                    assistant.enrich_task_descriptions(limit)
                    app.client.chat_postMessage(
                        channel=command['channel_id'],
                        text=f"✅ Task enrichment completed! Check Asana for updated task descriptions."
                    )
                except Exception as e:
                    app.client.chat_postMessage(
                        channel=command['channel_id'],
                        text=f"❌ Error during task enrichment: {str(e)}"
                    )
            
            thread = threading.Thread(target=run_enrichment)
            thread.start()
            
        except Exception as e:
            say(f"Error starting enrichment: {str(e)}")
    
    elif subcommand == "phase":
        # Get details for a specific phase
        if not content or not content.isdigit():
            say("Please specify a phase number. For example: `/assistant phase 1`")
            return
        
        phase_num = content
        
        if phase_num not in IMPLEMENTATION_PHASES:
            say(f"Phase {phase_num} not found in the implementation plan.")
            return
        
        phase = IMPLEMENTATION_PHASES[phase_num]
        
        # Format the response
        response = f"*{phase['name']}*\n"
        
        if phase['description']:
            response += f"{phase['description']}\n\n"
        
        if phase['key_activities']:
            response += "*Key Activities:*\n"
            for activity in phase['key_activities']:
                response += f"• {activity}\n"
            response += "\n"
        
        if phase['deliverables']:
            response += "*Deliverables:*\n"
            for deliverable in phase['deliverables']:
                response += f"• {deliverable}\n"
        
        say(response)
    
    else:
        # Unknown command
        say(f"Unknown command: {subcommand}\nType `/assistant help` to see available commands.")

def show_help(say):
    """Display help information about available commands"""
    say("*AI Implementation Assistant - Available Commands*\n\n"
        "• `/assistant help` - Show this help message\n"
        "• `/assistant ask [question]` - Ask the AI expert\n"
        "• `/assistant tasks` - Show upcoming tasks\n"
        "• `/assistant status` - Show implementation progress\n"
        "• `/assistant phase [number]` - Get details about a specific phase\n"
        "• `/assistant enrich [limit]` - Add detailed descriptions to tasks")

# Handle direct mentions of the bot
@app.event("app_mention")
def handle_mention(event, say):
    """Handle when someone @mentions the bot in Slack"""
    # Get the text of the message excluding the bot mention
    text = event.get("text", "")
    user = event.get("user", "")
    
    # Remove the mention part (e.g., <@U12345>)
    if BOT_ID:
        mention_format = f"<@{BOT_ID}>"
        text = text.replace(mention_format, "").strip()
    
    # If no text, prompt for a question
    if not text:
        say(f"Hi <@{user}>! How can I help you? Ask me anything about the implementation process.")
        return
    
    # Process as a question
    assistant = AIAssistant()
    response = assistant.ask_question(text)
    
    if response:
        # Save the conversation context
        conversation_key = f"slack-{user}"
        if conversation_key not in conversation_history:
            conversation_history[conversation_key] = []
        
        # Add to conversation history
        conversation_history[conversation_key].append({
            "role": "user",
            "content": text
        })
        conversation_history[conversation_key].append({
            "role": "assistant", 
            "content": response
        })
        
        # Respond in thread if it's a thread
        thread_ts = event.get("thread_ts", event.get("ts"))
        say(text=response, thread_ts=thread_ts)
    else:
        say(f"Sorry <@{user}>, I couldn't get an answer to that question. Please try rephrasing or using the `/assistant ask` command.")

#################################################
#                   MAIN                        #
#################################################

async def interactive_session():
    """Run an interactive AI session"""
    print(f"=== {ASSISTANT_NAME} ===")
    
    # Ask about model preference
    print("\nSelect AI model:")
    print("1. GPT-3.5 Turbo (default, faster)")
    print("2. GPT-4 (if available, more advanced)")
    model_choice = input("> ").strip()
    
    model = "gpt-3.5-turbo"
    if model_choice == "2":
        model = "gpt-4"
    
    assistant = AIAssistant(model=model)
    
    while True:
        print("\nWhat would you like to ask? (type 'exit' to quit)")
        question = input("> ")
        
        if question.lower() in ['exit', 'quit', 'bye']:
            break
        
        response = assistant.ask_question(question)
        
        if response:
            print("\n--- RESPONSE FROM AI EXPERT ---")
            print(response)
            print("-------------------------------------")
        else:
            print("Failed to get a response")
    
    print("Session ended")

async def process_asana_tasks(limit):
    """Process specified number of Asana tasks"""
    assistant = AIAssistant()
    await assistant.process_tasks(limit)

if __name__ == "__main__":
    """
    Main application entry point
    
    This function handles the different modes of operation:
    1. CLI mode - For direct interaction with the AI expert
    2. Task processing mode - For enriching Asana tasks
    3. Slack bot mode - For team interaction (default)
    
    Command line arguments:
        --cli: Run in CLI mode
        --tasks N: Process N Asana tasks
        No args: Start Slack bot
    """
    import argparse
    parser = argparse.ArgumentParser(description='AI Implementation Assistant')
    parser.add_argument('--tasks', type=int, help='Number of Asana tasks to process')
    parser.add_argument('--cli', action='store_true', help='Run in CLI mode')
    parser.add_argument('--slack', action='store_true', help='Run Slack bot')
    args = parser.parse_args()
    
    if args.cli:
        # CLI interactive mode
        asyncio.run(interactive_session())
    elif args.tasks:
        # Process Asana tasks
        asyncio.run(process_asana_tasks(args.tasks))
    else:
        # Default: Run with Slack bot
        print(f"Starting {ASSISTANT_NAME}...")
        
        # Get the bot's user ID
        get_bot_id()
        
        # Create a queue for command processing
        command_queue = queue.Queue()
        
        # Function to process commands
        def process_commands():
            while True:
                try:
                    print("\nType 'run' to manually run the task enrichment process.")
                    print("Type 'ask' to ask a question in CLI mode.")
                    print("Type 'enrich' to add detailed descriptions to tasks.")
                    print("Type 'quit' to exit the application.")
                    cmd = input("> ").strip().lower()
                    command_queue.put(cmd)
                    
                    # Short sleep to prevent high CPU usage
                    time.sleep(0.1)
                except Exception as e:
                    print(f"Command input error: {e}")
                    time.sleep(1)
        
        # Start command processing in a separate thread
        cmd_thread = threading.Thread(target=process_commands, daemon=True)
        cmd_thread.start()
        
        # Create the socket mode handler
        handler = SocketModeHandler(app, SLACK_APP_TOKEN)
        
        # Run in main thread but allow for checking command queue
        import signal
        
        # Define the signal handler for graceful shutdown
        def signal_handler(sig, frame):
            print("Shutting down gracefully...")
            sys.exit(0)
        
        # Set up signal handler in main thread
        signal.signal(signal.SIGINT, signal_handler)
        
        # Start the socket handler in a non-blocking way
        socket_thread = threading.Thread(target=handler.connect, daemon=True)
        socket_thread.start()
        
        print("Slack bot started! Use /assistant commands in your Slack workspace.")
        
        # Main loop to process commands from the queue
        while True:
            try:
                # Check for commands with a timeout to keep the main thread responsive
                try:
                    cmd = command_queue.get(timeout=1.0)
                    if cmd == "run":
                        print("Running task enrichment manually...")
                        asyncio.run(process_asana_tasks(limit=3))
                    elif cmd == "ask":
                        print("Entering CLI question mode...")
                        asyncio.run(interactive_session())
                    elif cmd == "enrich":
                        print("Enriching task descriptions...")
                        # Ask for limit
                        limit_input = input("How many tasks to enrich? (Enter for all): ").strip()
                        limit = int(limit_input) if limit_input.isdigit() else None
                        assistant = AIAssistant()
                        assistant.enrich_task_descriptions(limit)
                    elif cmd == "quit":
                        print("Exiting application...")
                        break
                    else:
                        print(f"Unknown command: {cmd}")
                except queue.Empty:
                    # No command, continue
                    pass
                    
                # Sleep briefly to prevent high CPU usage
                time.sleep(0.1)
            except KeyboardInterrupt:
                print("Shutting down...")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(1)
        
        print(f"{ASSISTANT_NAME} stopped.")
        sys.exit(0) 