import re
import sys
import traceback

DEBUG = 0

dispatch_var_db = {}
dispatch_func_db = {}

def print_it(*args,**kwargs):
    
    if (DEBUG):
        print(*args, **kwargs)
#
#----------------------------------------------------------------------
#

def add_var_value(var, value):
    var = var.lower()
    dispatch_var_db[var] = value

def add_function(name, func):
    name = name.lower()
    dispatch_func_db[name] = func

def get_var_value(var, quiet=False):
    var_l = var.lower()
    
    if (var_l in dispatch_var_db):
        val = dispatch_var_db[var_l]
    else:
        if (not quiet):
            print("Unknown variable", var, file=sys.stderr)
            
        val = None

    return val

def call_func(funcname, kwargs):
    funcname_l = funcname.lower()

    if (funcname_l in dispatch_func_db):

        f = dispatch_func_db[funcname_l]
        
        print_it("Calling:", funcname, "(", str(f), ")", "with", kwargs)
        try:
            val = f(**kwargs)

        except TypeError:
            
            val = None
            print("Invalid arguments for", funcname, file=sys.stderr)

            traceback.print_exc()
        
    else:
        print("Unknown function", funcname, file=sys.stderr)
        val = None

    return val

#
#----------------------------------------------------------------------
#


def get_next_token(s):
    token = None
    rest_of_s = ""
    ok = True
    
    # Remove leading spaces
    s = s.lstrip()

    # If non-empty string, look for either:
    
    #   a) a variable/function name
    #   b) an integer or floating point number
    #   c) a quoted string (with ") - no escaping of the quote permitted
    #   d) a quoted string (with ') - no escaping of the quote permitted
    #   e) a single "special" char (e.g. +, -, .)
    
    if ((s is not None) and (s != "")):
        m = re.search(
            r"^(" +
              r"(?:_*[a-zA-Z]\w*)|" +
              r"(?:\d+(?:\.\d+)?)|" +
              r"(?:\"[^\"]*\")|" +
              r"(?:'[^']*')|" +
              r"(?:.))" +
              r"(.*)$",
            s)

        if (m is not None):
            token = m.group(1)
            rest_of_s = m.group(2)

        else:
            print("Could not find next token in:", s, file=sys.stderr)
            ok = False

    return (token, rest_of_s, ok)
        
#
#----------------------------------------------------------------------
#
prev_tokens = None

def get_all_tokens(s):

    global prev_tokens

    # Handle a continuation line
    if (prev_tokens is not None):
        tokens = prev_tokens
        prev_tokens = None
        
    else:
        tokens = []
    
    ok = True
    thing = None
    
    while ((s != "") and (ok)):
        (token, s, ok) = get_next_token(s)

        # End of line comment?  Then eat the rest of the line
        if (token == "#"):
            s = ""
            
        elif (token is not None):
            tokens.append(token)

    # Handle a continuation line
    if (ok and (len(tokens) > 0) and (tokens[-1] == "\\")):
        # Save up to (but not including) the backslash at the end
        prev_tokens = tokens[:-1]

        # Return nothing so far
        tokens = []
        
    return (tokens, ok)
#
#----------------------------------------------------------------------
#

def decode_token(token):
    thing = None
    thingType = None
    
    # Figure out what the token is

    if (token is None):
        thing = None
        thingType = "N"
        
    # a string?

    elif ((token[0] == "'") or (token[0] == '"')):
        
        thing = token[1:-1]   # Remove the two quotes
        thingType = "s"
        
    # a number?
    elif (token[0].isdigit()):
        if ("." in token):
            thing = float(token)  # Convert to float
            thingType = "f"
        else:
            thing = int(token)
            thingType = "i"

    # a variable or function?
    elif ((token[0] == "_") or (token[0].isalpha())):
        thing = token
        thingType = "v/f"

    # Must be a punctuation
    else:
        thing = token
        thingType = "p"

    if (DEBUG > 3):
        print_it("Token:", '"' + str(thing) + '"', "is a", thingType)
    
    return (thing, thingType)


#
#----------------------------------------------------------------------
#

def split_assignment(tokens):
            
    ok = True
    val = None
    varname = None
    
    if (len(tokens) > 2):
        #
        #   Handle variable name first
        #
        (varname, varType) = decode_token(tokens[0])
        
        # Eat the variable name
        del tokens[0]
        
        # Var needs to be an alphanumeric
        if (varType != "v/f"):
            ok = False
            print("Invalid variable/argument name", varname, file=sys.stderr)
    else:
        print("Assignment operators must be in the form var=value", file=sys.stderr)
        ok = False

    #
    #  Now handle the = portion
    #
    if (ok and (len(tokens) > 1)):
        
        if (tokens[0] == "="):
            # Eat the = sign
            del tokens[0]
        else:
            print("Need an equals sign after var/argument name", varname, file=sys.stderr)
            ok = False
        

    if (ok and (len(tokens) > 0)):

        (val, ok) = decode_expr(tokens)
        
        if (val is None):
            print("Error with value for", varname, file=sys.stderr)
            ok = False


    if ((ok) and (DEBUG > 1)):
        print_it("EXPR:", varname, "IS", val)
        
    return (varname, val, ok)

#
#----------------------------------------------------------------------
#

def decode_func(funcname, tokens):
    ok = True
    kwargs = {}

    # Eat the opening paren '('
    if len(tokens) > 0:
        del tokens[0]
        ok = True
    else:
        print("Decode_func() called with an empty list!", funcname, file=sys.stderr)
        ok = False
        
    while (ok and (len(tokens) > 0) and (tokens[0] != ")")): 
        
        (varname, val, ok) = split_assignment(tokens) 

        if (ok):
           kwargs[varname] = val 
   
        if (ok and (len(tokens) > 0) and (tokens[0] == ",")):
            # Eat the comma and continue
            del tokens[0]
            
        elif (ok and (len(tokens) > 0) and (tokens[0] != ")")):
            print("Extra items or no closing parenthesis in function call", tokens, file=sys.stderr)
            ok = False
            thing = None
              

    if (ok):
        # Eat the closing paren
        if len(tokens) > 0:
            del tokens[0]
            
            # Now call the function
            thing = call_func(funcname, kwargs)
        else:
            print("No closing parenthesis for", funcname, file=sys.stderr)
            ok = False
            thing = None

    else:
        thing = None

    return (thing, ok)

#
#----------------------------------------------------------------------
#

def decode_factor(tokens):

    (thing, thingType) = decode_token(tokens[0])
    ok = True
    del tokens[0]
    
    # Need to decode a variable from a function

    if (thingType == "v/f"):
        
        # Functions would next have an open paren '('
        if ((len(tokens) > 0) and (tokens[0] == "(")):
            (thing, ok) = decode_func(thing, tokens)

        else:
            thing = get_var_value(thing)

    elif (thing == "("):

        # Next, look for an embedded expression
        (thing, ok) = decode_expr(tokens)

        if (ok and (len(tokens) > 0) and (tokens[0] == ")")):
            # Eat the closing paren
            del tokens[0]
            
        else:
            print("Missing closing parenthesis", file=sys.stderr)
            
            thing = None
            ok = False
            
    elif (thing == "+"):
        # Ignore leading + (eat it and look for another factor)
        (thing, ok) = decode_factor(tokens)

    elif (thing == "-"):
        # Grab the - (eat it and look for another factor)
        (thing, ok) = decode_factor(tokens)
        
        if (isinstance(thing, int) or isinstance(thing, float)):
            thing = -thing

        else:
            print("Cannot take the negative of", thing, file=sys.stderr)
        
            thing = None
            ok = False

        
    # (else term is already decoded - just use it)

    if (DEBUG > 2):
        print_it("TERM: Thing =", thing)
    
    return (thing, ok)


#
#
#
def decode_term(tokens):
    (thing1, ok) = decode_factor(tokens)

    while ((ok) and (len(tokens) > 0) and ((tokens[0] == "*") or (tokens[0] == "/"))):
        operator = tokens[0]
        del tokens[0]
        
        (thing2, ok) = decode_factor(tokens)

        thing1_ok = (isinstance(thing1, float) or isinstance(thing1, int))
        thing2_ok = (isinstance(thing2, float) or isinstance(thing2, int))

        if (ok and thing1_ok and thing2_ok):
            
            if (operator == "*"):
                thing1 = thing1 * thing2
                
            else:
                if (thing2 == 0):
                    print_it("Cannot divide by zero", thing1, thing2, file=sys.stderr)
                    
                    thing1 = None
                    ok = False
                    
                else:
                    thing1 = thing1 / thing2
                
        else:
            print_it("Cannot multiple/divide non-numbers", thing1, "&", thing2, file=sys.stderr)
        
            thing1 = None
            ok = False
            
    return (thing1, ok)

    
#
#----------------------------------------------------------------------
#

def decode_expr(tokens):
    
    if (len(tokens) > 0):

        (thing1, ok) = decode_term(tokens)
        
        while ((ok) and (len(tokens) > 0) and ((tokens[0] == "+") or (tokens[0] == "-"))):
            operator = tokens[0]
            del tokens[0]
            
            (thing2, ok) = decode_term(tokens)

            thing1_num = (isinstance(thing1, float) or isinstance(thing1, int))
            thing2_num = (isinstance(thing2, float) or isinstance(thing2, int))

            if (thing1_num and thing2_num):
                
                if (operator == "+"):
                    thing1 = thing1 + thing2
                else:
                    thing1 = thing1 - thing2

            # String concatenation?
            elif (isinstance(thing1,str) and isinstance(thing2,str) and (operator == "+")):
                thing1 = thing1 + thing2

            else:
                print_it("Cannot add/subtract", thing1, "&", thing2, file=sys.stderr)
                thing1 = None
                ok = False
                            
    if (DEBUG > 1):
        print_it("EXPR: Thing =", thing1)
    
    return (thing1, ok)

#
#----------------------------------------------------------------------
#

def dispatch_line(s):
    thing = None
    
    if (DEBUG > 0):
        print_it("LINE(input):", s.lstrip())

    (tokens, ok) = get_all_tokens(s)

    # No error during tokenization and tokens found?
    
    if ((ok) and (len(tokens) > 0)):
        
        # An assignment operator?
        if ((len(tokens) > 1) and (tokens[1] == "=")):
            (var, value, ok) = split_assignment(tokens)

            if (ok):
                add_var_value(var, value)

            #thing = value
            thing = None    # Assignment operators return no value (for HTML reasons)
            
        else:
            # Otherwise, an "output" statement
            (thing, ok) = decode_expr(tokens)

    # Extra cruft at the end of the line?  Tell the user
    if ((ok) and (len(tokens) > 0)):
        print("Unexpected extra items at the end of the string", tokens[0],
              file=sys.stderr)

        thing=None
        ok=False

    print_it("LINE(output):", thing)
    print_it("\n")

    return (thing, ok)

#
#----------------------------------------------------------------------
#

def dispatch_lines(lines):
    s_out = ""
    ok = True
    
    for s in lines.split("\n"):
        if (ok):
            (thing, ok) = dispatch_line(s)
            
        if (ok):
            s_out = s_out + str(thing) + "\n"
        else:
            s_out = ""

    return (s_out, ok)

#
#----------------------------------------------------------------------
#
def replace_inline(s):
    
    # Look for things in {{...}}
    m = re.search(r"^(.*?){{(.*?)}}(.*)$", s, re.DOTALL)

    s_out = ""
    
    while (m is not None):
        # Don't recursively replace things in {{ ... }}
        s_out  = s_out + m.group(1)
        (out, ok) = dispatch_line(m.group(2))

        if (ok and (out is not None)):
            s_out = s_out + str(out)
            
        s = m.group(3)
        m = re.search(r"^(.*?){{(.*?)}}(.*)$", s, re.DOTALL)

    s_out = s_out + s
        
    return s_out


def replace_inline_f(infile):
    f = open(infile)

    s_out = ""
    
    for line in f.readline():
        s_out = s_out + replace_inline(line)

    f.close()
    
    return s_out
        
#
#----------------------------------------------------------------------
#
def cmd_max(a = None, b=None):
    m = None

    # https://stackoverflow.com/questions/354038/how-do-i-check-if-a-string-represents-a-number-float-or-int
    if isinstance(a,str) and a.replace('.','',1).isdigit():
        a = float(a)

    if isinstance(b,str) and b.replace('.','',1).isdigit():
        b = float(b)

    if isinstance(a, int) or isinstance(a, float):
        m = a

    if isinstance(b, int) or isinstance(b, float):
        if b > a:
            m = b

    return m


#
#----------------------------------------------------------------------
#
def cmd_min(a = None, b=None):
    m = None

    # https://stackoverflow.com/questions/354038/how-do-i-check-if-a-string-represents-a-number-float-or-int
    if isinstance(a,str) and a.replace('.','',1).isdigit():
        a = float(a)

    if isinstance(b,str) and b.replace('.','',1).isdigit():
        b = float(b)

    if isinstance(a, int) or isinstance(a, float):
        m = a

    if isinstance(b, int) or isinstance(b, float):
        if b < a:
            m = b

    return m

#
#----------------------------------------------------------------------
#

add_function("min", cmd_min)
add_function("max", cmd_max)

#
#----------------------------------------------------------------------
#
if (__name__ == "__main__"):
    def printit(s):
        print(s)

        
    add_var_value("a", 1)
    add_var_value("b", 2)

    add_function("say_hello",   lambda: print("Hello World"))
    add_function("say_goodbye", lambda: print("Goodbye!"))
    add_function("print", printit)
    
    add_function("add_nums",    lambda x=1, y=1 : x+y)

    dispatch_lines("""
# This line should be ignored
        say_hello()
        "hi mark"
        a  # Comment should be ignored
        c="hello"
        c
        c + " y'all"
        1+2
        100-90
        (200-100)
        (200-50)/2
        d=100-90
        d
        10-7
        4*8
        8/2
        e=(100-20)/2
        e
        f=add_nums(x=10,y=20)
        f
        #10/0
        ((100-90)*(3-2))+(5+2)-(7-7)
        9*2+100/5
        a+b
        "hi " + "mark"
        add_nums()
        add_nums(x=10,y=20)
        say_goodbye()

        t = "hello"
        print(s=t)

        s= "string (with embedded parens) should be fine"
        print(s=s)
        
        """)

    s = replace_inline("2 + 2 = {{2+2}} and 4 + 4 = {{ 4 + 4 }}")
    print(s)
