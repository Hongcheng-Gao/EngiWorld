def generate_func(json_data):
    # Collect all class names and their functions.
    class_funcs = {}
    no_class_funcs = []

    for item in json_data:
        if item["type"] == "function":
            func = item["function"]
            func_parts = func["name"].split(".")

            if len(func_parts) == 2:
                class_name, func_name = func_parts
                if class_name not in class_funcs:
                    class_funcs[class_name] = []
                class_funcs[class_name].append(item)
            else:
                no_class_funcs.append(item)

    code = ""

    # Generate functions belonging to classes.
    for class_name, funcs in class_funcs.items():
        code += f"class {class_name}:\n"
        for item in funcs:
            func = item["function"]
            func_name = func["name"].split(".")[-1]
            description = func["description"]
            params = func["parameters"]["properties"]
            required = func["parameters"].get("required", [])

            # Build the parameter list.
            param_list = ["cls"]
            # Add required parameters first.
            for param_name in required:
                param_list.append(f"{param_name}")
            # Then add optional parameters.
            for param_name in params:
                if param_name not in required:
                    param_list.append(f"{param_name}")  # Set optional parameter defaults to None.

            # Build the function definition.
            func_def = f"    def {func_name}({', '.join(param_list)}):\n"

            # Build the docstring.
            docstring = f'        """\n        {description}\n\n        Args:\n'
            if len(param_list) == 1:  # Only the cls parameter is present.
                docstring += "            None\n"
            else:
                # Document required parameters first.
                for param_name in required:
                    param_type = params[param_name]["type"]
                    param_desc = params[param_name].get("description", "")
                    docstring += f"            {param_name} ({param_type}): {param_desc}\n"
                # Then document optional parameters.
                for param_name in params:
                    if param_name not in required:
                        param_type = params[param_name]["type"]
                        param_desc = params[param_name].get("description", "")
                        docstring += f"            {param_name} ({param_type}, optional): {param_desc}\n"

            docstring += '        """\n'

            code += func_def + docstring + "\n"

        code += "\n"

    # Generate functions without a class.
    for item in no_class_funcs:
        func = item["function"]
        func_name = func["name"]
        description = func["description"]
        params = func["parameters"]["properties"]
        required = func["parameters"].get("required", [])

        # Build the parameter list.
        param_list = []
        # Add required parameters first.
        for param_name in required:
            param_list.append(f"{param_name}")
        # Then add optional parameters.
        for param_name in params:
            if param_name not in required:
                param_list.append(f"{param_name}")

        # Build the function definition.
        func_def = f"def {func_name}({', '.join(param_list)}):\n"

        # Build the docstring.
        docstring = f'    """\n    {description}\n\n    Args:\n'
        if not param_list:
            docstring += "        None\n"
        else:
            # Document required parameters first.
            for param_name in required:
                param_type = params[param_name]["type"]
                param_desc = params[param_name].get("description", "")
                docstring += f"        {param_name} ({param_type}): {param_desc}\n"
            # Then document optional parameters.
            for param_name in params:
                if param_name not in required:
                    param_type = params[param_name]["type"]
                    param_desc = params[param_name].get("description", "")
                    docstring += f"        {param_name} ({param_type}, optional): {param_desc}\n"

        docstring += '    """\n'

        code += func_def + docstring + "\n"

    return code.strip()


if __name__ == "__main__":
    import json

    with open("libreoffice_calc.json", "r") as f:
        json_data = json.load(f)
    print(generate_func(json_data))
