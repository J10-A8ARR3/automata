from flask import Flask, request, jsonify
import re
from tabulate import tabulate

optAssg = r'(\+=|\-=|\*=|/=|%=|\~=|=)'
optUni = r'(\+\+|\-\-)'
optArtm = r'(\=|\+|\-|\*|\/|\%|\~|\^)'
optLog = r'(\!|\|\||&&)'
optRel = r'(==|!=|>|<|>=|<=)'

# Define token types

TOKEN_TYPES = {
    'OPERATOR_ASSIGNMENT': optAssg,
    'UNARY_OPERATOR': optUni,
    'OPERATOR_ARITHMETIC': optArtm,
    'OPERATOR_LOGIC': optLog,
    'OPERATOR_RELATION': optRel,
    'KEYWORDS': r'\b(int|string|char|float|double|bool|long|if|else|while|scan|break|default|print'
                r'|false|none|true|and|as|assert|continue|def|del|elif|except|finally|for|from|global|import'
                r'|in|is|lambda|nonlocal'
                r'|not|or|pass|raise|return|try|with|yield)\b',
    'RESERVEDWORDS': r'(kdelete|kremove|kupdate|ksection|ktotal|kadd|ksub|financial_statement|asset|liability|equity|revenues|expenses|gains'
                     r'|losses|net_income|operating|investing|financing|ocbalance|ccbalance|bank_system|baccount|bafreeze|baclose'
                     r'|account_number|account_holder|credit|debit|account_balance|brdeposit|brwithdraw|brtransfer|bcpayroll|bcrollout|bcemployee|rate'
                     r'|overtime|earnings|net_pay|deductions|taxes|benefits|biloan|biinvest|principal|interest_rate|time_period|compound_interest'
                     r'|simple_interest|return_on_investment|loan_amount|installment_amount|interest_rate|loan_term|total_payment)',
    'INT_LITERAL': r'\b\d+\b',
    'STRING_LITERAL': r'"([^"\\]*(\\.[^"\\]*)*)"',
    'IDENTIFIER': r'[a-zA-Z_][a-zA-Z0-9_]*',
    'SINGLE_LINE_COMMENT': r'(#.*)$',
    'APOSTROPHE': r"'",
    'QUOTATION_SIGN': r'"',
    'COMMA': r',',
    'COLON': r':',
    'SEMICOLON': r';',
    'LBRACE': r'{',
    'RBRACE': r'}',
    'LPAREN': r'\(',
    'RPAREN': r'\)',
    'LBRACKET': r'\[',
    'RBRACKET': r'\]',
    'DATA_BINDING_START': r'<%',
    'DATA_BINDING_END': r'%>',
    'WHITE_SPACE': r'\s+',
    'VALUE_SIGN': r':',
    'NEWLINE': r'\n',
    'ERROR': r'.',
}


def tokenize_line(line):
    code_tokens = []
    comment_token = None
    # Tokenize the code part of the line
    for match in re.finditer(
             r'#.*|\b\w+\b|"(?:[^"\\]*(?:\\.[^"\\]*)*)"|\'(?:[^\'\\]*(?:\\.[^\'\\]*)*)\'|\S|print\s*\(.*?\)\s*|(\+\+|\-\-|[\+\-\*\%\~\^])|(\|\||&&|==|!=|>=?|<=?)|\+|\-|\*|\/|\%|\~|\^|\!|(\()|(\))',
            line):
        word = match.group()
        if word.startswith("#"):  # If it's a single-line comment
            comment_token = ('SINGLE_LINE_COMMENT', word)
            break
        # Check if it matches any pattern
        for token_type, pattern in TOKEN_TYPES.items():
            if re.fullmatch(pattern, word):
                code_tokens.append((token_type, word))
                break
        else:
            code_tokens.append(('UNKNOWN', word))
    return code_tokens, comment_token

def tokenize(input_string):
    tokens = []
    multi_line_comment = ''
    in_multi_line_comment = False
    lines = input_string.split('\n')
    for line in lines:
        if in_multi_line_comment:
            end_index = line.find('*/')
            if end_index != -1:
                multi_line_comment += line[:end_index]
                tokens.append(('MULTI_LINE_COMMENT', multi_line_comment))
                multi_line_comment = ''
                in_multi_line_comment = False
                line = line[end_index + 2:]
            else:
                multi_line_comment += line + '\n'
                continue
        start_index = line.find('/*')
        if start_index != -1:
            end_index = line.find('*/', start_index)
            if end_index != -1:
                tokens.extend(tokenize_line(line[:start_index]))
                tokens.append(('MULTI_LINE_COMMENT', line[start_index + 2:end_index]))
                tokens.extend(tokenize_line(line[end_index + 2:]))
            else:
                tokens.extend(tokenize_line(line[:start_index]))
                multi_line_comment = line[start_index + 2:] + '\n'
                in_multi_line_comment = True
        else:
            line_tokens, _ = tokenize_line(line)  # Ignore comment tokens for syntax analysis
            tokens.extend(line_tokens)

    # Filter out None values
    tokens = [token for token in tokens if token and token != []]

    return tokens


def syntax_analyzer(tokens):
    # Initialize flags
    int_declaration = False
    string_declaration = False
    char_declaration = False
    float_declaration = False
    double_declaration = False
    bool_declaration = False
    long_declaration = False
    in_multi_line_comment = False
    in_if_else_block = False


    # Iterate through tokens
    for token_type, token_value in tokens:

        # Skip tokens inside a multi-line comment
        if in_multi_line_comment:
            # Check for end of multi-line comment
            if token_type == 'MULTI_LINE_COMMENT' and token_value.endswith('*/'):
                in_multi_line_comment = False
            continue


        # Check for multi-line comment start
        if token_type == 'MULTI_LINE_COMMENT' and token_value.startswith('/*'):
            in_multi_line_comment = True
            continue

        if in_multi_line_comment:
            continue

        # Check for variable declaration syntax
        if token_type == 'KEYWORDS' and token_value in {'int', 'string', 'char', 'float', 'double', 'bool', 'long'}:
            next_index = tokens.index((token_type, token_value)) + 1
            if next_index < len(tokens) and tokens[next_index][0] == 'IDENTIFIER':
                next_index += 1
                if next_index < len(tokens):
                    if tokens[next_index][1] == '=':
                        next_index += 1
                        if token_value == 'int' and next_index < len(tokens) and tokens[next_index][0] == 'INT_LITERAL':
                            int_declaration = True
                        elif token_value == 'string' and next_index < len(tokens) and tokens[next_index][0] == 'STRING_LITERAL':
                            string_declaration = True
                        elif token_value == 'char' and next_index < len(tokens) and tokens[next_index][0] == 'CHAR_LITERAL':
                            char_declaration = True
                        elif token_value == 'float' and next_index < len(tokens) and tokens[next_index][0] == 'INT_LITERAL':
                            float_declaration = True
                        elif token_value == 'double' and next_index < len(tokens) and tokens[next_index][0] == 'INT_LITERAL':
                            double_declaration = True
                        elif token_value == 'bool' and next_index < len(tokens) and tokens[next_index][0] in {'true', 'false'}:
                            bool_declaration = True
                        elif token_value == 'long' and next_index < len(tokens) and tokens[next_index][0] == 'INT_LITERAL':
                            long_declaration = True
                        else:
                            return f"Syntax Error: {token_value} declaration should have {token_value} literal value"
                    elif tokens[next_index][1] == ';':

                        # Declaration without assignment is valid
                        if token_value == 'int':
                            int_declaration = True
                        elif token_value == 'string':
                            string_declaration = True
                        elif token_value == 'char':
                            char_declaration = True
                        elif token_value == 'float':
                            float_declaration = True
                        elif token_value == 'double':
                            double_declaration = True
                        elif token_value == 'bool':
                            bool_declaration = True
                        elif token_value == 'long':
                            long_declaration = True
                    else:
                        return f"Syntax Error: Expected an assignment operator '=' after '{token_value}' declaration"
                else:
                    # Declaration without assignment is valid at the end of the line
                    if token_value == 'int':
                        int_declaration = True
                    elif token_value == 'string':
                        string_declaration = True
                    elif token_value == 'char':
                        char_declaration = True
                    elif token_value == 'float':
                        float_declaration = True
                    elif token_value == 'double':
                        double_declaration = True
                    elif token_value == 'bool':
                        bool_declaration = True
                    elif token_value == 'long':
                        long_declaration = True
            else:
                return f"Syntax Error: Expected an identifier after '{token_value}' declaration"

        if token_type == 'TOKEN_KSUB':
            next_index = tokens.index((token_type, token_value)) + 1
            if next_index < len(tokens) and tokens[next_index][0] == 'LPAREN':
                next_index += 1
                # Check for sysSecStatement parameter
                if next_index < len(tokens) and tokens[next_index][0] == 'TOKEN_SYS_SEC_STATEMENT':
                    next_index += 1
                    if next_index < len(tokens) and tokens[next_index][0] == 'COMMA':
                        next_index += 1
                        # Check for subIndex parameter
                        if next_index < len(tokens) and tokens[next_index][0] == 'TOKEN_SUB_INDEX':
                            next_index += 1
                            if next_index < len(tokens) and tokens[next_index][0] == 'COMMA':
                                next_index += 1
                                # Check for subLabel parameter
                                if next_index < len(tokens) and tokens[next_index][0] == 'TOKEN_SUB_LABEL':
                                    next_index += 1
                                    if next_index < len(tokens) and tokens[next_index][0] == 'COMMA':
                                        next_index += 1
                                        # Check for subList parameter
                                        if next_index < len(tokens) and tokens[next_index][0] == 'TOKEN_SUB_LIST':
                                            return "Valid 'ksub' function statement"
                                        else:
                                            return "Syntax Error: Missing or invalid 'subList' parameter"
                                    else:
                                        return "Syntax Error: Missing comma ',' after 'subLabel' parameter"
                                else:
                                    return "Syntax Error: Missing or invalid 'subLabel' parameter"
                            else:
                                return "Syntax Error: Missing comma ',' after 'subIndex' parameter"
                        else:
                            return "Syntax Error: Missing or invalid 'subIndex' parameter"
                    else:
                        return "Syntax Error: Missing comma ',' after 'sysSecStatement' parameter"
                else:
                    return "Syntax Error: Missing or invalid 'sysSecStatement' parameter"
            else:
                return "Syntax Error: Missing opening parenthesis '(' in 'ksub' function"
            

            # Check for ksub function syntax
        if token_type == 'TOKEN_KADD':
            next_index = tokens.index((token_type, token_value)) + 1
            if next_index < len(tokens) and tokens[next_index][0] == 'LPAREN':
                next_index += 1
                # Check for sysSecStatement parameter
                if next_index < len(tokens) and tokens[next_index][0] == 'TOKEN_SYS_SEC_STATEMENT':
                    next_index += 1
                    if next_index < len(tokens) and tokens[next_index][0] == 'COMMA':
                        next_index += 1
                        # Check for subIndex parameter
                        if next_index < len(tokens) and tokens[next_index][0] == 'TOKEN_ADD_INDEX':
                            next_index += 1
                            if next_index < len(tokens) and tokens[next_index][0] == 'COMMA':
                                next_index += 1
                                # Check for subLabel parameter
                                if next_index < len(tokens) and tokens[next_index][0] == 'TOKEN_ADD_LABEL':
                                    next_index += 1
                                    if next_index < len(tokens) and tokens[next_index][0] == 'COMMA':
                                        next_index += 1
                                        # Check for subList parameter
                                        if next_index < len(tokens) and tokens[next_index][0] == 'TOKEN_ADD_LIST':
                                            return "Valid 'kadd' function statement"
                                        else:
                                            return "Syntax Error: Missing or invalid 'addList' parameter"
                                    else:
                                        return "Syntax Error: Missing comma ',' after 'addLabel' parameter"
                                else:
                                    return "Syntax Error: Missing or invalid 'addLabel' parameter"
                            else:
                                return "Syntax Error: Missing comma ',' after 'addIndex' parameter"
                        else:
                            return "Syntax Error: Missing or invalid 'addIndex' parameter"
                    else:
                        return "Syntax Error: Missing comma ',' after 'sysSecStatement' parameter"
                else:
                    return "Syntax Error: Missing or invalid 'sysSecStatement' parameter"
            else:
                return "Syntax Error: Missing opening parenthesis '(' in 'kadd' function"
            
        if token_type == 'TOKEN_KTOTAL':
            next_index = tokens.index((token_type, token_value)) + 1
            if next_index < len(tokens) and tokens[next_index][0] == 'LPAREN':
                next_index += 1
                # Check for sysSecStatement parameter
                if next_index < len(tokens) and tokens[next_index][0] == 'TOKEN_SYS_SEC_STATEMENT':
                    next_index += 1
                    if next_index < len(tokens) and tokens[next_index][0] == 'COMMA':
                        next_index += 1
                        # Check for subIndex parameter
                        if next_index < len(tokens) and tokens[next_index][0] == 'TOKEN_SYS_SEC_NAME':
                            next_index += 1
                            if next_index < len(tokens) and tokens[next_index][0] == 'COMMA':
                                next_index += 1
                                # Check for subLabel parameter
                                if next_index < len(tokens) and tokens[next_index][0] == 'COMMA':
                                    next_index += 1
                                        # Check for subList parameter
                                    if next_index < len(tokens) and tokens[next_index][0] == 'TOKEN_ADD_LIST':
                                        return "Valid 'ktotal' function statement"
                                    else:
                                        return "Syntax Error: Missing or invalid 'sysSecName' parameter"
                                else:
                                    return "Syntax Error: Missing comma ',' after 'sysSecTitle' parameter"
                            else:
                                return "Syntax Error: Missing opening parenthesis '(' in 'ktotal' function"

        if token_type == 'TOKEN_BANKSYSTEM':
            next_index = tokens.index((token_type, token_value)) + 1
            if next_index < len(tokens) and tokens[next_index][0] == 'LPAREN':
                next_index += 1
                # Check for sysSecStatement parameter
                if next_index < len(tokens) and tokens[next_index][0] == 'TOKEN_BANKNAME':
                    next_index += 1
                    if next_index < len(tokens) and tokens[next_index][0] == 'COMMA':
                        next_index += 1
                        # Check for subIndex parameter
                        if next_index < len(tokens) and tokens[next_index][0] == 'TOKEN_RESERVEAMMOUNT':
                            next_index += 1
                            if next_index < len(tokens) and tokens[next_index][0] == 'COMMA':
                                next_index += 1
                                return "Valid 'bankSytem' function statement"
                            else:
                                return "Syntax Error: Missing or invalid 'bankName' parameter"
                        else:
                            return "Syntax Error: Missing comma ',' after 'reserveAmmount' parameter"
                    else:
                        return "Syntax Error: Missing opening parenthesis '(' in 'bankSystem' function"

        if token_type == 'TOKEN_BACCOUNT':
            next_index = tokens.index((token_type, token_value)) + 1
            if next_index < len(tokens) and tokens[next_index][0] == 'LPAREN':
                next_index += 1
                # Check for sysSecStatement parameter
                if next_index < len(tokens) and tokens[next_index][0] == 'TOKEN_ACCOUNTID':
                    next_index += 1
                    if next_index < len(tokens) and tokens[next_index][0] == 'COMMA':
                        next_index += 1
                        # Check for subIndex parameter
                        if next_index < len(tokens) and tokens[next_index][0] == 'TOKEN_ACCOUNT_HOLDER':
                            next_index += 1
                            if next_index < len(tokens) and tokens[next_index][0] == 'COMMA':
                                next_index += 1
                                # Check for subLabel parameter
                                if next_index < len(tokens) and tokens[next_index][0] == 'COMMA':
                                    next_index += 1
                                        # Check for subList parameter
                                    if next_index < len(tokens) and tokens[next_index][0] == 'TOKEN_ACCOUNT_TYPE':
                                        return "Valid 'baccount' function statement"
                                    else:
                                        return "Syntax Error: Missing or invalid 'accountID' parameter"
                                else:
                                    return "Syntax Error: Missing comma ',' after 'accountHolder' parameter"
                            else:
                                return "Syntax Error: Missing or invalid 'accountType' parameter"
                        else:
                            return "Syntax Error: Missing opening parenthesis '(' in 'baccount' function"
        
        # Check for if-else block syntax
        if token_type == 'KEYWORDS' and token_value in {'if', 'elif'}:
            next_index = tokens.index((token_type, token_value)) + 1
            if next_index < len(tokens) and tokens[next_index][0] == 'LPAREN':
                next_index += 1
                if tokens[next_index][0] in {'INT_LITERAL', 'IDENTIFIER'}:
                    next_index += 1  # Advance to the next token
                    if next_index < len(tokens) and tokens[next_index][0] == 'OPERATOR_RELATION':
                        next_index += 1  # Advance to the next token
                        if tokens[next_index][0] in {'INT_LITERAL', 'IDENTIFIER'}:
                            next_index += 1  # Advance to the next token
                            if tokens[next_index][0] == 'RPAREN':
                                next_index += 1  # Advance to the next token
                                return "Valid conditional Statement"

                            else:
                                return "Syntax Error: Expected ')' after the conditional expression"
                        else:
                            return "Syntax Error: Expected an expression after the relational operator"
                    else:
                        return "Syntax Error: Expected a relational operator after the conditional expression"

        # Check for 'else' block syntax
        if token_type == 'KEYWORDS' and token_value == 'else':
            next_index = tokens.index((token_type, token_value)) + 1
            if next_index < len(tokens):
                if tokens[next_index][0] == '{':
                    print("'else' block syntax is correct.")
                elif tokens[next_index][0] == 'KEYWORDS' and tokens[next_index][1] == 'if':
                    print("'else if' block syntax is correct.")
                else:
                    return "Valid else syntax"
            else:
                return "Syntax Error: Incomplete 'else' statement"

        # Check the Syntax for 'For' loop
        if token_type == 'KEYWORDS' and token_value == 'for':
            next_index = tokens.index((token_type, token_value)) + 1
            if next_index < len(tokens) and tokens[next_index][0] == 'LPAREN':
                next_index += 1
                # Check if there is an initialization expression
                while next_index < len(tokens) and tokens[next_index][0] != 'SEMICOLON':
                    next_index += 1
                if next_index < len(tokens) and tokens[next_index][0] == 'SEMICOLON':
                    next_index += 1  # Skip the semicolon
                    # Check if there is a condition expression
                    while next_index < len(tokens) and tokens[next_index][0] != 'SEMICOLON':
                        next_index += 1
                    if next_index < len(tokens) and tokens[next_index][0] == 'SEMICOLON':
                        next_index += 1  # Skip the semicolon
                        # Check if there is an increment expression
                        while next_index < len(tokens) and tokens[next_index][0] != 'RPAREN':
                            next_index += 1
                        if next_index < len(tokens) and tokens[next_index][0] == 'RPAREN':
                            return "Valid 'for' loop statement"
                        else:
                            return "Syntax Error: Missing closing parenthesis ')' in 'for' loop"
                    else:
                        return "Syntax Error: Missing second semicolon ';' in 'for' loop"
                else:
                    return "Syntax Error: Missing first semicolon ';' in 'for' loop"
            else:
                return "Syntax Error: Missing opening parenthesis '(' in 'for' loop"

        # Check for 'while' loop syntax
        if token_type == 'KEYWORDS' and token_value == 'while':
            next_index = tokens.index((token_type, token_value)) + 1
            if next_index < len(tokens) and tokens[next_index][0] == 'LPAREN':
                next_index += 1
                # Check if there is a condition expression
                while next_index < len(tokens) and tokens[next_index][0] != 'RPAREN':
                    next_index += 1
                if next_index < len(tokens) and tokens[next_index][0] == 'RPAREN':
                    return "Valid 'while' loop statement"
                else:
                    return "Syntax Error: Missing closing parenthesis ')' in 'while' loop"
            else:
                return "Syntax Error: Missing opening parenthesis '(' in 'while' loop"

        # Check for data binding syntax
        if token_type == 'DATA_BINDING_START':
            next_index = tokens.index((token_type, token_value)) + 1
            # Check if there is content between data binding delimiters
            while next_index < len(tokens) and tokens[next_index][0] != 'DATA_BINDING_END':
                next_index += 1
            if next_index < len(tokens) and tokens[next_index][0] == 'DATA_BINDING_END':
                return "Valid data binding syntax"
            else:
                return "Syntax Error: Missing closing delimiter '%' for data binding"

        # Check for Reserved words syntax
        if token_type == 'RESERVEDWORDS':
            next_index = tokens.index((token_type, token_value)) + 1
            if next_index < len(tokens) and tokens[next_index][0] == 'LPAREN':
                next_index += 1
                # Check if there is content between parentheses
                while next_index < len(tokens) and tokens[next_index][0] != 'RPAREN':
                    next_index += 1
                if next_index < len(tokens) and tokens[next_index][0] == 'RPAREN':
                    return f"Valid invocation of reserved word '{token_value}'"
                else:
                    return f"Syntax Error: Missing closing parenthesis ')' after reserved word '{token_value}'"
            else:
                return f"Syntax Error: Missing opening parenthesis '(' after reserved word '{token_value}'"
                # Check the Syntax for print function

        if token_type == 'KEYWORDS' and token_value == 'print':
            next_index = tokens.index((token_type, token_value)) + 1
            if next_index < len(tokens) and tokens[next_index][0] == 'LPAREN':
                next_index += 1
                if next_index < len(tokens) and tokens[next_index][0] in {'STRING_LITERAL', 'INT_LITERAL',
                                                                          'IDENTIFIER'}:
                    next_index += 1
                    if next_index < len(tokens) and tokens[next_index][0] == 'RPAREN':
                        return "Valid 'print' statement"
                    else:
                        return "Syntax Error: Missing closing parenthesis ')' after string literal"
                else:
                    return "Syntax Error: Missing or invalid string literal argument for 'print' statement"
            else:
                return "Syntax Error: Missing opening parenthesis '(' for 'print' statement"

    # Prompt the message based on the analysis
    if int_declaration:
        return "Valid Integer declaration"
    elif string_declaration:
        return "Valid String declaration"
    elif char_declaration:
        return "Valid Char declaration"
    elif float_declaration:
        return "Valid Float declaration"
    elif double_declaration:
        return "Valid Double declaration"
    elif bool_declaration:
        return "Valid Boolean declaration"
    elif long_declaration:
        return "Valid Long declaration"
    else:
        return "Invalid Syntax"


def print_tokens(tokens):
    print(tabulate(tokens, headers=["Lexemes", "Tokens"]))

def print_results(results):
    print(tabulate(results, headers=["Code", "Parser Result"]))

# Read the code from a .kc file
def read_code_from_file(filename):
    with open(filename, 'r') as file:
        return file.read()

# Read code from a .kc file
input_string = read_code_from_file("input.kc")

tokens = tokenize(input_string)

# Print the tokens
print_tokens(tokens)
print("\n")

results = []
# Iterate through lines of input and analyze each line
lines = input_string.split('\n')

# Display the Errors
for i, line in enumerate(lines):
    line = line.strip()
    if not line:
        continue
    line_tokens = tokenize_line(line)
    result = syntax_analyzer(line_tokens[0])
    if "Error" in result:
        print(f"\nInvalid Syntax on line {i + 1}: {line.strip()}" "\n" f"{result.split('Syntax Error: ')[1]}")

print("\n")
for i, line in enumerate(lines):
    line = line.strip()
    if not line:
        continue
    line_tokens = tokenize_line(line)
    result = syntax_analyzer(line_tokens[0])
    results.append((line, result))

# Print the code-parser result table
print_results(results)

print("\n")

app = Flask(__name__)

@app.route('/analyze', methods=['POST'])
def analyze_code():
    # Get the code from the POST request
    code = request.get_json().get('code', '')
    
    # Perform tokenization and syntax analysis
    tokens = tokenize(code)
    results = []
    lines = code.split('\n')
    for i, line in enumerate(lines):
        line_tokens = tokenize_line(line)
        result = syntax_analyzer(line_tokens[0])
        results.append((line, result))
    
    # Convert the results into a JSON response
    response = jsonify({
        'tokens': [{'lexeme': t[1], 'token': t[0]} for t in tokens],
        'results': [{'code': r[0], 'result': r[1]} for r in results]
    })
    
    # Return the response
    return response

if __name__ == '__main__':
    app.run(debug=True)