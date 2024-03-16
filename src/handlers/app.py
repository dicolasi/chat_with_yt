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
        self.last_question = None
        self.last_response = None

    def process_video(self, url: str):
        yt_handler = YTHandler(url)
        self.current_transcript = yt_handler.get_formatted_transcript()
        return "Video processed. You can start asking questions now."

    def chat_with_video(self, message):
        if not self.current_resolver:
            return "Please select an AI model first.", ""
        self.last_question = message
        combined_input = f"Context: {self.current_transcript}\nQuestion: {message}"
        response = self.current_resolver.query([{"content": combined_input, "role": "user"}])
        self.last_response = response[0]
        return response[0], ""

    def handle_feedback(self, feedback):
        print(f"Feedback received for '{self.last_question}': {feedback}")
        with open('feedback.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([self.last_question, self.last_response, feedback])
        self.last_question = None
        self.last_response = None
        return "Thank you for your feedback!"

    def build_ui(self):
        with gr.Blocks() as app:
            with gr.Row():
                gr.Markdown("<h1>YouTube Video Processor and Chat</h1>")
            with gr.Row():
                gr.Markdown("<h3>Enter a YouTube video URL and use the chatbox to ask questions about the video.</h3>")
            with gr.Row():
                video_url = gr.Textbox(label="YouTube Video URL", placeholder="Enter YouTube URL here...")
                process_button = gr.Button("Process Video")
                process_output = gr.Text(label="Status")
            process_button.click(self.process_video, inputs=video_url, outputs=process_output)

            resolver_dropdown = gr.Dropdown(list(self.resolvers.keys()), label="Choose AI Resolver")
            resolver_dropdown.change(self.update_resolver, resolver_dropdown)

            msg = gr.Textbox(placeholder="Enter your question here...", container=False)
            ask_button = gr.Button("Ask")
            chatbot_response = gr.Textbox(placeholder="Response from AI will appear here...", container=False)
            # Removed 'msg' from the outputs of the ask_button.click to keep the question in the textbox
            ask_button.click(self.chat_with_video, inputs=msg, outputs=[chatbot_response])

            # Setup msg to submit on Enter key and trigger chat_with_video without clearing the msg
            msg.submit(self.chat_with_video, inputs=msg, outputs=[chatbot_response])

            feedback_options = gr.Radio(choices=["Thumbs up 👍", "Thumbs down 👎"], label="Feedback on this response")
            feedback_submit = gr.Button("Submit Feedback")
            feedback_message = gr.Textbox(label="Feedback Status", container=False)

            def submit_feedback_and_clear(feedback):
                if not self.last_response or not feedback:
                    feedback_message = "Please select feedback and ensure there's a response to provide feedback on."
                    return feedback_message, "", ""  # Ensure to clear both the response and the question
                feedback_result = self.handle_feedback(feedback)
                feedback_options.value = ""  # Clear feedback selection
                # Clear the chatbot response and the question textbox as feedback is submitted
                return feedback_result, "", ""

            feedback_submit.click(submit_feedback_and_clear, inputs=feedback_options,
                                  outputs=[feedback_message, chatbot_response, msg])

        return app

    def update_resolver(self, resolver_name):
        self.current_resolver = self.resolvers[resolver_name]
