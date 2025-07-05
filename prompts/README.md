# InnerLoop Agent Prompts

This folder contains the system prompts for each agent in the InnerLoop architecture. Storing prompts as separate markdown files provides several benefits:

1. **Version Control**: Track changes to prompts over time
2. **Easy Editing**: Modify agent behavior without touching code
3. **Experimentation**: Test different prompt variations
4. **Documentation**: Prompts serve as clear documentation of agent roles

## File Structure

- `shared_identity.md` - Common identity shared by all agents (templated)
- `experiencer.md` - System prompt for the Experiencer agent
- `stream_generator.md` - System prompt for the Stream Generator
- `attention_director.md` - System prompt for the Attention Director

## How It Works

1. When an agent initializes, it loads its prompts from these files
2. The `shared_identity.md` is templated with values from `config.yaml`
3. Agent-specific prompts are appended to the shared identity
4. If files are missing, the system falls back to inline prompts

## Customization

Feel free to modify these prompts to experiment with different agent behaviors:

- Adjust personality traits in `shared_identity.md`
- Change thought generation patterns in `stream_generator.md`
- Modify attention criteria in `attention_director.md`
- Alter conversation style in `experiencer.md`

## Template Variables

The `shared_identity.md` file supports these template variables:
- `{name}` - Agent's name
- `{age}` - Agent's age
- `{background}` - Background description
- `{personality}` - Personality traits
- `{interests}` - List of interests

These values are pulled from `config.yaml` under `agents.shared_identity`.