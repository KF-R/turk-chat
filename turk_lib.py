import sys, time, re

def print_log(log_string = '',log_to_file=True, noStdOut = True):
    LOG_FILENAME = sys.argv[0].split('.')[0] + '.log'

    timestamp = time.strftime("%m/%d/%y  %H:%M:%S", time.localtime(time.time()))
    if not noStdOut: print(f"[ {timestamp} ] {log_string}")

    if(log_to_file):
        with open(LOG_FILENAME, "a") as file:
            file.write(f"[ {timestamp} ] {log_string}\n")
            

import re

# Precomputed lists
ONES = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
TEENS = ["ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "ten", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
TEEN_REPLACEMENTS = {TEENS[i]: ONES[i] for i in range(1, 10)}

def replace_tens_teens_with_ones(input_string: str) -> str:
    for teen, replacement in TEEN_REPLACEMENTS.items():
        input_string = input_string.replace(teen, replacement)

    for i in range(2, 10):
        input_string = input_string.replace(TENS[i], ONES[i])

    return input_string

def convert_to_words(number) -> str:
    if number == 0:
        return "zero"
    
    if_negative = 'minus ' if number < 0 else ''
    number = abs(number)

    def convert_chunk(n):
        if n < 10:
            return ONES[n]
        if n < 20:
            return TEENS[n - 10]
        if n < 100:
            return TENS[n // 10] + (" " + ONES[n % 10] if n % 10 != 0 else "")
        return ONES[n // 100] + " hundred" + (" " + convert_chunk(n % 100) if n % 100 != 0 else "")

    # Handling large numbers (trillion and above) with direct computation
    if number >= 1000000000000:
        exponent = len(str(number)) - 1
        mantissa = round(number / 10**exponent, 2)
        high, low = divmod(int(mantissa * 100), 100)
        return f"{if_negative}{convert_chunk(high)}{('' if mantissa == round(mantissa) else ' point ' + convert_chunk(low))} times ten to the power of {convert_chunk(exponent)}"

    parts = []
    for divisor, name in [(1000000000, "billion"), (1000000, "million"), (1000, "thousand")]:
        if number >= divisor:
            parts.append(convert_chunk(number // divisor) + " " + name)
            number %= divisor
    parts.append(convert_chunk(number))

    return ' '.join(parts)

def number_to_words(input_str: str) -> str:
    
    if_negative = 'minus ' if input_str.startswith('-') else ''
    input_str = input_str.lstrip('-')

    parts = input_str.replace(',', '').split('.')
    integer_part = int(parts[0])
    words = if_negative + convert_to_words(integer_part)

    if len(parts) > 1:
        decimal_digits = [ONES[int(digit)] if digit != '0' else 'zero' for digit in parts[1]]
        words += ' point ' + ' '.join(decimal_digits)

    return words

def convert_complete_number_string(number_string: str) -> str:
    number_regex = r'(?<!\d)-?\d+(?:,\d{3})*(?:\.\d+)?|\b-?\d*\.\d+\b'

    def replace_match(match):
        number_value = match.group(0)
        return number_to_words(number_value)

    return re.sub(number_regex, replace_match, number_string)
