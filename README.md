

# AI Implementation Assistant

A customizable assistant that helps organizations implement specialized processes by integrating Asana task management with AI-powered expertise based on your proprietary implementation guide.

## 📋 Overview

This AI Implementation Assistant streamlines complex processes by:

- Providing expert guidance based on your organization's knowledge base
- Managing and enriching implementation tasks in Asana
- Offering a Slack interface for team communication
- Following a structured implementation approach defined in your Path.txt

## 🔧 Features

### Asana Integration
- Automatically enriches Asana tasks with context-aware guidance
- Tracks implementation progress across defined phases
- Suggests relevant tasks based on your implementation requirements

### Slack Commands
- `/assistant ask [question]` - Get answers from the AI expert
- `/assistant tasks` - View active implementation tasks
- `/assistant phase [number]` - Get details about a specific implementation phase
- `/assistant status` - View implementation progress
- `/assistant enrich` - Add detailed descriptions to tasks based on your Path.txt

### AI Expertise
- Provides detailed explanations tailored to your implementation process
- Offers implementation guidance specific to your context
- Generates task descriptions with compliance and best practice information

## 🛠️ Setup

### Prerequisites
- Python 3.8+
- An Asana workspace with a project for your implementation
- A Slack workspace with permissions to add bots
- API credentials for Asana and Slack
- OpenAI API key

### Installation

1. Clone this repository:
   ```bash
   git clone [repository-url]
   cd ai-implementation-assistant
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your credentials:
   ```
   # Slack credentials
   SLACK_BOT_TOKEN=xoxb-your-token
   SLACK_APP_TOKEN=xapp-your-token
   
   # Asana credentials
   ASANA_TOKEN=your-asana-token
   ASANA_PROJECT_ID=your-asana-project-id
   
   # OpenAI API
   OPENAI_API_KEY=your-openai-api-key
   
   # Optional: Custom name for your assistant
   ASSISTANT_NAME=Your Custom Assistant Name
   ```

4. Create your Path.txt file:
   - This should contain your implementation methodology
   - Include phase definitions like "PHASE 1: Planning & Setup (Week 1-2)"
   - Add detailed requirements, steps, and domain knowledge

5. Configure Slack App:
   - Create a new Slack app at https://api.slack.com/apps
   - Enable Socket Mode
   - Add Bot Token Scopes: `app_mentions:read`, `chat:write`, `commands`
   - Create a Slash Command: `/assistant`
   - Enable Events API and subscribe to `app_mention` events
   - Install the app to your workspace

6. Import your implementation structure into Asana:
   - Create a new Asana project
   - Set up your task structure based on your implementation phases

### Running the Assistant

```bash
python ai_assistant.py
```

## 📊 Customizing Path.txt

The Path.txt file is the knowledge base for your AI assistant. Here's how to structure it:

1. **Start with an overview** of what's being implemented
2. **Define implementation phases** using the format:
   ```
   PHASE 1: Planning & Setup (Week 1-2)
   ```
3. **List key activities** for each phase
4. **Include relevant requirements** or standards
5. **Add domain-specific knowledge** that the assistant should reference
6. **Define deliverables** expected from each phase

The more detailed your Path.txt file, the more knowledgeable your assistant will be.

## 🖥️ Usage Examples

### CLI Mode
```bash
python ai_assistant.py --cli
```

This starts an interactive session where you can ask questions directly.

### Process Asana Tasks
```bash
python ai_assistant.py --tasks 5
```

This will process and enrich 5 tasks in your Asana project.

### Slack Bot Mode
```bash
python ai_assistant.py
```

This starts the Slack bot, allowing team members to interact via commands or direct mentions.

## 📝 Command Reference

### Slack Commands
- `/assistant help` - Show available commands
- `/assistant ask [question]` - Ask the AI expert
- `/assistant tasks` - Show upcoming tasks
- `/assistant status` - Show implementation progress
- `/assistant phase [number]` - Get details about a specific phase
- `/assistant enrich [limit]` - Add detailed descriptions to tasks

### Direct Mention
You can also interact with the assistant directly by mentioning it in Slack:
- `@AI Assistant What is the next step in our implementation?`
- `@AI Assistant How do I complete this deliverable?`

### CLI Commands
While the assistant is running, you can use these commands in the terminal:
- `run` - Manually run the task enrichment process
- `ask` - Enter CLI question mode
- `enrich` - Add detailed descriptions to tasks
- `quit` - Exit the application

## 🔍 Troubleshooting

- **Missing credentials**: Ensure all required credentials are in your `.env` file
- **Path.txt not loaded**: Check that Path.txt exists in the same directory as the script
- **Slack connection issues**: Verify your Slack app is correctly configured with proper scopes
- **Asana task errors**: Ensure your Asana project ID is correct and your token has proper permissions
- **OpenAI API errors**: Check your API key and billing status

## 🔒 Security Note

This application stores credentials in the `.env` file. Ensure this file:
- Is included in your `.gitignore`
- Has restricted access permissions
- Is not shared or committed to public repositories

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
