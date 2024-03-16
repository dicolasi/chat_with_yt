import csv
from typing import Dict

import gradio as gr

from src.handlers.yt_handler import YTHandler
from src.models.config import load_resolvers
from src.models.resolver import AIChatResolverBase


class GradioApp:
    def __init__(self, config_path):
        self.resolvers: Dict[str, AIChatResolverBase] = load_resolvers(file_path=config_path)
        self.current_resolver = None
        self.current_transcript = ""
        self.last_question = None  # Track the last question asked
        self.last_response = None  # Track the last response received

    def process_video(self, url: str):
        yt_handler = YTHandler(url)
        self.current_transcript = yt_handler.get_formatted_transcript()
        return "Video processed. You can start asking questions now."

    def chat_with_video(self, message):
        if not self.current_resolver:
            return "Please select an AI model first.", ""
        self.last_question = message  # Update the last question
        combined_input = f"Context: {self.current_transcript}\nQuestion: {message}"
        response = self.current_resolver.query([{"content": combined_input, "role": "user"}])
        self.last_response = response[0]  # Update the last response
        return response[0], ""

    def handle_feedback(self, feedback):
        # Here, you should implement saving feedback logic.
        print(f"Feedback received for '{self.last_question}'-'{self.last_question}': {feedback}")

        # Simulate saving feedback.
        with open('feedback.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([self.last_question, self.last_response, feedback])

        self.last_question = None  # Resetting last question after feedback.
        self.last_response = None  # Resetting last response after feedback.
        return "Thank you for your feedback!"

    def build_ui(self):
        with gr.Blocks() as app:
            with gr.Row():
                gr.Markdown("<h1>YouTube Video Processor and Chat</h1>")
            with gr.Row():
                gr.Markdown(
                    "<h3>Enter a YouTube video URL and use the chatbox to ask "
                    "questions about the video.</h3>")

            with gr.Row():
                video_url = gr.Textbox(label="YouTube Video URL", placeholder="Enter YouTube URL here...", scale=6)
                process_button = gr.Button("Process Video")
                process_output = gr.Text(label="Status", scale=3)

                resolver_dropdown = gr.Dropdown(list(self.resolvers.keys()), label="Choose AI Resolver", scale=3)
                resolver_dropdown.change(self.update_resolver, resolver_dropdown)

            with gr.Row():
                msg = gr.Textbox(placeholder="Enter your question here...", container=False, scale=12)
                ask_button = gr.Button("Ask")


            with gr.Row():
                chatbot_response = gr.Textbox(placeholder="Chatbot response will appear here", container=False,
                                              show_copy_button=True)
            ask_button.click(self.chat_with_video, inputs=msg, outputs=[chatbot_response, msg])

            with gr.Row():
                feedback_options = gr.Radio(choices=["Thumbs up 👍", "Thumbs down 👎"], label="Feedback on this response")
            with gr.Row():
                feedback_submit = gr.Button("Submit Feedback")

            # Bind the process_video function to the process_button
            process_button.click(self.process_video, inputs=video_url, outputs=process_output)

            # Bind the chat_with_video function to the msg Textbox
            msg.submit(self.chat_with_video, inputs=msg, outputs=[chatbot_response, msg])

            # Feedback submission logic
            def submit_feedback_and_clear(feedback):
                self.handle_feedback(feedback)
                chatbot_response.value = ""
                msg.value = ""
                feedback_options.value = ""  # Clear the selection
                return "", "", ""  # Clear the outputs

            feedback_submit.click(submit_feedback_and_clear, inputs=feedback_options,
                                  outputs=[feedback_options, chatbot_response, msg])

        return app

    def update_resolver(self, resolver_name):
        self.current_resolver = self.resolvers[resolver_name]
