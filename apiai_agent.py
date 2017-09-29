import apiai
import json

CLIENT_ACCESS_TOKEN = '7ea5bd62bba447129820c6a8dc88215f'

ai = apiai.ApiAI(CLIENT_ACCESS_TOKEN)

def get_response(query_text):
    request = ai.text_request()
    request.query = query_text
    response = json.loads(request.getresponse().read().decode('utf-8'))
    responseStatus = response["status"]["code"]
    if 200 == responseStatus:
        # Sending the textual response of the bot.
        return response["result"]["fulfillment"]["speech"]
    else:
        return "Извините, я не понял."
