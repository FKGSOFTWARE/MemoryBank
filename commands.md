*In memoryBank repo terminal*
# Install requirements
```pip install -r requirement.txt```
# Navigate to MemoryBank-SiliconFriend/SiliconFriend-ChatGPT/
```cd SiliconFriend-ChatGPT```
# Export API Key or add dotenv to 'silicon_friend_api'
```export OPENAI_API_KEY xxxx```
# Run serverside for the API
```./launch_api.sh```

*In goodAI repo terminal*
# Run the benchmark
```python.exe runner\run_benchmark.py -c .\configurations\ltm_dev_benchmarks\dev_benchmark_4-1.yml -a memory_bank```
