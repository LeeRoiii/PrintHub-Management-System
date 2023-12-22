#verification.py
from flask import request
import logging

from Config import VERIFY_TOKEN, PAGE_ACCESS_TOKEN
 
 
def verify():
     """Endpoint to verify the webhook."""
     mode = request.args.get('hub.mode')
     token = request.args.get('hub.verify_token')
     challenge = request.args.get('hub.challenge')
     
     logging.debug(f"Received Verification: mode={mode}, token={token}, challenge={challenge}")
     
     if mode == 'subscribe' and token == VERIFY_TOKEN:
         return challenge
     return 'Failed validation', 403