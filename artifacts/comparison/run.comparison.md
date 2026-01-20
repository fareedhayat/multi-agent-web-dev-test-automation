# MCP Comparison (Runtime, Tokens, Tools)

## Playwright MCP
- Runtime: 2041.39s
- Input tokens: 7,689,260
- Output tokens: 62,142
- Tokens/sec: 3766.67
- Output/Input ratio: 0.008082
- Avg suite duration: 291.61s
- Tool calls: 177
- Tool errors: 0
- Avg tool duration: 4.60s
- Top tools: browser_evaluate(62), browser_run_code(45), browser_navigate(26), browser_click(15), browser_snapshot(7), browser_take_screenshot(5), browser_type(5), browser_console_messages(4), browser_wait_for(4), browser_press_key(2)

## Selenium MCP (Angie)
- Runtime: 1048.61s
- Input tokens: 2,993,880
- Output tokens: 28,881
- Tokens/sec: 2855.11
- Output/Input ratio: 0.009647
- Avg suite duration: 149.80s
- Tool calls: 253
- Tool errors: 0
- Avg tool duration: 1.52s
- Top tools: find_element(86), click_element(49), take_screenshot(32), navigate(24), send_keys(22), get_element_text(15), press_key(8), start_browser(7), hover(7), close_session(3)

## Selenium Server1
- Runtime: 1198.55s
- Input tokens: 6,596,424
- Output tokens: 42,305
- Tokens/sec: 5503.69
- Output/Input ratio: 0.006413
- Avg suite duration: 170.10s
- Tool calls: 251
- Tool errors: 3
- Avg tool duration: 1.55s
- Top tools: run_javascript_and_get_console_output(77), check_page_ready(33), run_javascript_in_console(31), take_screenshot(20), get_an_element(20), navigate(17), click_to_element(15), set_value_to_input_element(12), get_elements(9), get_console_logs(6)
