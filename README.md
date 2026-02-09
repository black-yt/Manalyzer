<div align="center">
<h1>Manalyzer: End-to-end Automated Meta-analysis with Multi-agent System
</div>

<div align="center">

[![Official Site](https://img.shields.io/badge/Official%20Site-333399.svg?logo=homepage)](https://black-yt.github.io/meta-analysis-page/)&#160;
<a href="https://arxiv.org/pdf/2505.20310" target="_blank"><img src="https://img.shields.io/badge/arXiv-b5212f.svg?logo=arxiv" height="21px"></a>
[![Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97%20HuggingFace-gray)](https://huggingface.co/datasets/CoCoOne/Manalyzer)&#160;
[![GitHub](https://img.shields.io/badge/GitHub-000000?logo=github&logoColor=white)](https://github.com/black-yt/Manalyzer)&#160;

</div>

---

## 🆕 Updates/News

🚩 **Updates** (2026-02-09) Code has been released.

🚩 **Updates** (2025-05-22) Initial upload to arXiv [[PDF]](https://arxiv.org/pdf/2505.20310). The code will be released soon.



## 🎯 Abstract

<img src="./assets/comparison.png" width="100%" alt="main-results" align="center">

Meta-analysis is a systematic research methodology that synthesizes data from multiple existing studies to derive comprehensive conclusions. This approach not only mitigates limitations inherent in individual studies but also facilitates novel discoveries through integrated data analysis. Traditional meta-analysis involves a complex multi-stage pipeline including literature retrieval, paper screening, and data extraction, which demands substantial human effort and time. However, while LLM-based methods can accelerate certain stages, they still face significant challenges, such as hallucinations in paper screening and data extraction. In this paper, we propose a multi-agent system, Manalyzer, which achieves end-to-end automated meta-analysis through tool calls. The hybrid review, hierarchical extraction, self-proving, and feedback checking strategies implemented in Manalyzer significantly alleviate these two hallucinations. To comprehensively evaluate the performance of meta-analysis, we construct a new benchmark comprising 729 papers across 3 domains, encompassing text, image, and table modalities, with over 10,000 data points. Extensive experiments demonstrate that Manalyzer achieves significant performance improvements over the LLM baseline in multi meta-analysis tasks.

---


## 🚀 Method Overview

<img src="./assets/workflow.png" width="100%" alt="pipeline" align="center">

Manalyzer is a multi-agent system incorporating tool calling and feedback mechanisms, enabling end-to-end automated meta-analysis in real scientific research scenarios. We divide the meta-analysis process into three stages. The first stage involves receiving user input, searching for and downloading papers, followed by filtering out relevant and valuable ones. The second stage focuses on extracting data from these selected papers and integrating it into tables. The third stage is to analyze the integrated data and output the final meta-analysis report.

## 🔥 Quick Start

```bash
export LLM_API_KEY="your-api-key"
export LLM_BASE_URL="your-api-base-url"
export MINERU_TOKEN="your-mineru-api-key" # Apply for the API at https://mineru.net/

python workflow/main.py
```

## 📬 Contact Us

- 💬 **GitHub Issues**: Please open an issue for bug reports or feature requests

- 📧 **Email**: [xu_wanghan@sjtu.edu.cn](https://black-yt.github.io/)

---

## 📜 Citation

If you would like to cite our work, please use the following BibTeX.

```bib
@article{xu2025manalyzer,
  title={Manalyzer: End-to-end Automated Meta-analysis with Multi-agent System},
  author={Xu, Wanghan and Zhang, Wenlong and Ling, Fenghua and Fei, Ben and Hu, Yusong and Ren, Fangxuan and Lin, Jintai and Ouyang, Wanli and Bai, Lei},
  journal={arXiv preprint arXiv:2505.20310},
  year={2025}
}
```

---

## 🌟 Star History

If you find this work helpful, please consider to **star⭐** this [repo](https://github.com/black-yt/Manalyzer). Thanks for your support! 🤩

[![black-yt/Manalyzer Stargazers](https://reporoster.com/stars/black-yt/Manalyzer)](https://github.com/black-yt/Manalyzer/stargazers)

[![Star History Chart](https://api.star-history.com/svg?repos=black-yt/Manalyzer&type=date&legend=top-left)](https://www.star-history.com/#black-yt/Manalyzer&type=date&legend=top-left)

<p align="right"><a href="#top">🔝Back to top</a></p>