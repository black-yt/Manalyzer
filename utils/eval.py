from openai import OpenAI
import base64
from io import BytesIO

system_prompt= """
You are a domain expert in **<field>**, specializing in information extraction and data organization. Your task is to analyze the provided input (which may include text, images, or tables) and extract precisely the information relevant to the user's specified topics of interest.
The input may not be relevant to the user's needs. If it is not relevant, please return None. If it is relevant, please output the relevant data in the form of a markdown table.

**Topic of Interest**: <topic_of_interest>
**Required Data**: <required_data>
"""


query_prompt = """
# Input
<text_or_caption>
"""

field_dict = {
    "atmosphere": {
        'field': 'air pollutants', 
        'topic_of_interest': "Concentrations of Sulfate, Nitrate, Ammonium, Organic Carbon (OC) and Black Carbon (BC) at different locations.\nIncluding Record Numbers indicates the number of records.",
        'required_data': "Country, Province, City, Including Record Numbers, Sulfate, Nitrate, Ammonium, Organic Carbon, Black Carbon",
    }, 

    "agriculture": {
        'field': 'agriculture', 
        'topic_of_interest': "Food production in different regions. \nYear: The year for which the data was recorded.\nLatitude: The latitude of the planting location.\nLongitude: The longitude of the planting location.\nCrop: The type of crop grown, such as wheat or pulses.\nYield (conv. till) kg/ha: The yield of the crop using conventional tillage methods (tillage), in kilograms per hectare (kg/ha).\nYield (no-till) kg/ha: The yield of the crop using no-till methods (no tillage), in kilograms per hectare (kg/ha).",
        'required_data': "Year, Country, Location, Crop, Yield (conv. till) kg/ha, Yield (no-till) kg/ha",
    }, 

    "environment": {
        'field': 'environmental pollution', 
        'topic_of_interest': "Content of heavy metal pollutants in rivers in different regions.\nIf there are multiple pollutants in the same river, please list them in multiple rows.\nRiver: The name of the river.\nLocation: The country or region where the river is located.\nHeavy metals: Heavy metal pollutants in rivers.\nContent (µg/L): The amount of pollutants, in µg/L.",
        'required_data': "Rive, Location, Heavy metals, Content (µg/L)",
    }, 
}


class EvaluationModel:
    def __init__(self, field, topic_of_interest, required_data, api_key, base_url, model='gpt-4o'):
        self.system_prompt = system_prompt.replace('<field>', field).replace('<topic_of_interest>', topic_of_interest).replace('<required_data>', required_data)
        self.query_prompt = query_prompt
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def get_prompt(self, text_or_caption):
        system_prompt = self.system_prompt
        query_prompt = self.query_prompt.replace('<text_or_caption>', text_or_caption)
        return {'system_prompt': system_prompt, 'query': query_prompt}

    def get_response(self, query, system_prompt, **kwargs):
        image = kwargs.get('image', None)
        try:
            if image is None:  # without image
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query},
                    ],
                    max_tokens=2048,
                    temperature=0,
                )
            else:  # with image
                buffered = BytesIO()
                image.save(buffered, format="JPEG")
                buffered.seek(0)
                base64_image = base64.b64encode(buffered.read()).decode('utf-8')
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": [
                            {"type": "text", "text": query},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                            }
                        ]},
                    ],
                    max_tokens=2048,
                    temperature=0,
                )
        except Exception as e:
            print(f"Error: {e}")
            return 'Error in response'
        
        response = response.choices[0].message.content
        markdown_start = response.find('|')
        markdown_end = response.rfind('|')
        if markdown_start != -1 and markdown_end != -1:
            return response[markdown_start:markdown_end+1].strip()
        else:
            return 'None'
    