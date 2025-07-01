🚧 Toll Booth Legality Validator — Geospatial + LLM Automation
Detect and verify illegal toll booth placements using OpenStreetMap data, Dijkstra's algorithm, web scraping, and local LLM inference.

📌 Problem
According to NHAI rules in India, toll booths must be at least 60 km apart. However, violations exist due to unverified or duplicate booths. Manual verification is slow and error-prone.

✅ Solution
This pipeline:

Parses OpenStreetMap .pbf files with billions of nodes

Identifies toll booth pairs violating the 60 km legal separation rule

Scrapes real-world data about each toll booth using Selenium

Verifies each booth's legitimacy using a locally hosted LLM (Ollama + DeepSeek R1)

Classifies responses as valid or invalid using a TinyBERT binary classifier

Outputs a cleaned dataset of verified, compliant toll booths

⚙️ Tech Stack
Component	Tool/Library
Geospatial Data	OpenStreetMap (.pbf), Osmium
Distance Checks	Dijkstra's Algorithm + Haversine
Scraping	Selenium + Google Search
LLM Reasoning	Ollama (chatgpt, deepseek etc.)
Classification	Hugging Face TinyBERT
Language	Python (pandas, numpy, requests)

🔄 Pipeline Overview
Extract Toll Booths
→ Use osmium to parse .pbf and extract nodes with barrier=toll_booth

Find Violations
→ Compute shortest paths + Haversine distances between all booths
→ Keep only booth pairs < 60 km apart

Verify Existence
→ Scrape Google Search with Selenium using booth name + coordinates
→ Pass result to Ollama LLM for natural language verification

Classify Validity
→ Use TinyBERT to classify LLM response as valid (0) or invalid (1)
→ Drop invalid booths from the final result

📁 Output
Final CSV of toll booth pairs that are:

Less than 60 km apart and

Both verified as real toll booths

💡 Example Use Case
Government auditing of toll plaza legality

NGO investigations into highway policy violations

Compliance tools for transport infrastructure planning

📸 Screenshot (Optional)
You can include sample plots, network graphs, or scraped results here.

🛠️ To Do
 Add map visualization of valid/invalid pairs



📜 License
MIT — free to use, modify, and improve.

task: 1. Learn to use osm file--done
      2. find cords of all toll--done
      3. pair up nearest neighbours--done Using haversine..........todo--ids need to seperated regionwise
      4. determine how to calculate distance between two --done
      6. verification using selenium, chrome; grab names -- done
      7. setup 1st llm to scan web   -- done
      8. simple nlp to process above to return 0,1   -- pending
      9. clean names -- done
      10. Write git
      10. Write blog



----------------------------------------

Using osmconvert.exe:
'''
osmconvert map.pbf --out-osm -o=map.osm
'''

Eg.    osmconvert north-eastern-zone-latest.osm.pbf --out-osm -o=north-eastern-zone-latest.osm