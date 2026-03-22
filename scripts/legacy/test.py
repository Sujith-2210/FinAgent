import mlx.core as mx
from mlx_vlm import load, generate
import argparse

def main():
    parser = argparse.ArgumentParser(description="Generate a response from the mlx model.")
    parser.add_argument("--model", type=str, default="mlx-community/gemma-3-4b-it-4bit", help="The model path to use.")
    parser.add_argument("--prompt", type=str, default="Create a 3 day travel itinerary for Paris", help="The prompt to generate a response for.")
    parser.add_argument("--max-tokens", type=int, default=1024, help="The maximum number of tokens to generate.")
    args = parser.parse_args()

    # Load the model
    model, processor = load(args.model)

    # Format the prompt with special tokens
    formatted_prompt = f"<bos><start_of_turn>user\n{args.prompt}<end_of_turn>\n<start_of_turn>model\n"

    # Generate the response
    print("Agent Thinking...")
    response = generate(model, processor, prompt=formatted_prompt, verbose=False, max_tokens=args.max_tokens)

    # Print the response
    print("\nGenerated Response:")
    print(response.text)

if __name__ == "__main__":
    main()
