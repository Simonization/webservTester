# First, compile your webserv project
make

# Run general tests
python3 test_general.py ./webserv config/example.conf

# Run correction sheet tests  
python3 test_correction.py ./webserv config/example.conf

# For stress tests, install siege first
sudo apt-get install siege  # Linux
brew install siege  # macOS

Required (and present on 42 School Computers) (verify with command: whereis)
pip3 install psutil


Test Output
The tests provide colored output:

🟢 GREEN: Test passed
🔴 RED: Test failed
🟡 YELLOW: Warning or skipped
🔵 BLUE: Section headers

The correction sheet test will indicate if any failure would result in a grade of 0 (like memory leaks or missing I/O multiplexing).

Notes
The tests match the configuration structure in config/example.conf
CGI scripts (lotr.py and star_wars.sh) are tested
