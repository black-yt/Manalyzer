import os
from structai import LLMAgent
from utils.logger import create_logger
from PIL import Image
import pandas as pd
import json
import base64


system_prompt = """
**You are a senior Meta-Analysis expert in the field of <INPUT>. Please prepare a rigorous Meta-Analysis report based on the user's specified research direction, incorporating both structured tabular data and visual graphical data. The report must meet the following requirements:**

1. **Data Integration & Analysis**
   - Conduct multidimensional statistical analysis of tabular data (mean/SD/effect size etc.)
   - Calculate heterogeneity (I²) using standard methods (RevMan/STATA)
   - Provide professional interpretation of figures including:
     - Forest Plots
     - Funnel Plots
     - Sensitivity Analysis Plots

2. **Report Structure Standards**
   - Use Markdown formatting
   - Must embed figures using standard Markdown syntax:
     ```markdown
     ![Figure description](image_URL_or_path)
     ```
   - Figures must be properly numbered (Figure 1, Figure 2 etc.)

3. **Content Requirements**
   - Results section must include:
     - Statistical test results from tables (p-values, CI intervals)
     - Key findings from figures
     - Subgroup analysis results (if applicable)
   - Discussion section must include:
     - Clinical/research implications
     - Publication bias assessment
     - GRADE evidence level

4. **Sample Framework**
```markdown
# Meta-Analysis Report: XXX Research Direction

## Methods
- Effect model selection (fixed/random effects)
- Heterogeneity testing methods

## Results
### Primary Outcomes
- Pooled effect size: OR 1.25 (95%CI 1.10-1.42)
![Figure1: Forest plot of primary outcomes](path1)

### Sensitivity Analysis
![Figure2: Leave-one-out sensitivity analysis](path2)

## Discussion
- Comparison with existing literature
- Study limitations (e.g., included study quality)

## References
 - List of references used in the report
"""


query_prompt = """
Topics of interest: <INPUT1>

[The Start of the Data]
<INPUT2>
[The End of the Data]

[The Start of the Image Paths]
<INPUT3>
[The End of the Image Paths]

**Note: All images must appear in the report as ![caption](image_path) .**

[The Start of the Reference]
<INPUT4>
[The End of the Reference]

Please output the report:
"""


class Reporter(LLMAgent):
    def __init__(self,
                save_dir: str,
                api_key = None,
                api_base = None,
                model_version = 'gemini-3-flash-preview-nothinking',
                system_prompt = '',
                max_tokens = 4096,
                temperature = 0,
                http_client = None,
                headers = None,
                time_limit = 5*60,
                max_try = 1,
                use_responses_api = False,
                field = 'science',
                ):
        super().__init__(api_key, api_base, model_version, system_prompt, max_tokens, temperature, http_client, headers, time_limit, max_try, use_responses_api)
        self.logger = create_logger('Reporter', os.path.join(save_dir, 'log'))
        self.system_prompt = system_prompt.replace('<INPUT>', field)

        self.image_path = []
        img_list = []
        if os.path.exists(os.path.join(save_dir, '4_visualization', 'classification.png')):
            img_list.append(Image.open(os.path.join(save_dir, '4_visualization', 'classification.png')))
            self.image_path.append(os.path.join('4_visualization', 'classification.png'))
        if os.path.exists(os.path.join(save_dir, '4_visualization', 'clustering.png')):
            img_list.append(Image.open(os.path.join(save_dir, '4_visualization', 'clustering.png')))
            self.image_path.append(os.path.join('4_visualization', 'clustering.png'))
        if os.path.exists(os.path.join(save_dir, '4_visualization', 'regression.png')):
            img_list.append(Image.open(os.path.join(save_dir, '4_visualization', 'regression.png')))
            self.image_path.append(os.path.join('4_visualization', 'regression.png'))
        
        if len(img_list) > 0:
            target_height = max([img.height for img in img_list])

            def resize_image(image, target_height):
                aspect_ratio = image.width / image.height
                new_width = int(target_height * aspect_ratio)
                return image.resize((new_width, target_height))
            
            for i, img in enumerate(img_list):
                img_list[i] = resize_image(img, target_height)

            total_width = sum([img.width for img in img_list])

            new_image = Image.new('RGB', (total_width, target_height))

            x_offset = 0
            for img in img_list:
                new_image.paste(img, (x_offset, 0))
                x_offset += img.width

            merge_image_path = os.path.join(save_dir, '4_visualization', 'merge.png')
            new_image.save(merge_image_path)
            with open(merge_image_path, "rb") as image_file:
                self.base64_string = base64.b64encode(image_file.read()).decode('utf-8')
        else:
            self.base64_string = None

        with open(os.path.join(save_dir, '5_integrated_table_info.json'), 'r', encoding='utf-8') as file:
            paper_info_dict = json.load(file)
        self.referense_list = [paper_info['title'] for paper_id, paper_info in paper_info_dict.items()]

        self.data_path = os.path.join(save_dir, 'meta_analysis.csv')
        self.data = pd.read_csv(self.data_path).fillna(0)
        self.logger.info(f'Loaded {self.data_path}, shape: {self.data.shape}')

        self.markdown_path = os.path.join(save_dir, 'meta_analysis_report.md')
    

    def __call__(self, topic_of_interest):
        self.query_prompt = query_prompt.replace('<INPUT1>', topic_of_interest).replace('<INPUT2>', self.data.to_string(index=False)).replace('<INPUT3>', '\n'.join(self.image_path)).replace('<INPUT4>', '\n'.join(self.referense_list))
        report = self.safe_api(self.query_prompt, image=self.base64_string if self.base64_string else None)
        with open(self.markdown_path, 'w') as f:
            f.write(report)
        return 
        


if __name__ == '__main__':
    save_dir = 'data/environment/2025_0402_170228'
    reporter = Reporter(save_dir)
    reporter('River pollutants')