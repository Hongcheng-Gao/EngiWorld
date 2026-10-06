import json
import os
import subprocess
import sys

import uno
from com.sun.star.beans import PropertyValue


class CalcTools:
    localContext = uno.getComponentContext()
    resolver = localContext.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", localContext)
    ctx = resolver.resolve("uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
    desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    doc = desktop.getCurrentComponent()
    sheet = doc.CurrentController.ActiveSheet
    ret = ""

    @classmethod
    def close_other_window(cls):
        """Close every document except the current one."""
        # Get all open documents.
        components = cls.desktop.getComponents().createEnumeration()
        current_url = cls.doc.getURL()

        while components.hasMoreElements():
            doc = components.nextElement()
            if doc.getURL() != current_url:  # If this is not the current document.
                doc.close(True)  # True saves changes.

    @classmethod
    def maximize_window(cls):
        """
        Maximize the window within the work area.
        Use the work area excluding the taskbar and similar regions.
        """
        window = cls.doc.getCurrentController().getFrame().getContainerWindow()
        toolkit = window.getToolkit()
        device = toolkit.createScreenCompatibleDevice(0, 0)

        # Get the work area, excluding the taskbar and similar regions.
        workarea = toolkit.getWorkArea()

        # Set the window position and size to the work area.
        window.setPosSize(workarea.X, workarea.Y, workarea.Width, workarea.Height, 15)

    @classmethod
    def print_result(cls):
        print(cls.ret)

    @classmethod
    def save(cls):
        """
        Save the current workbook to its current location

        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            # Just save the document
            cls.doc.store()
            cls.ret = "Success"
            return True
        except Exception as e:
            cls.ret = f"Error: {e}"
            return False

    @classmethod
    def _get_column_index(cls, column_name, sheet=None):
        """
        Get the index of a column by its name (A, B, C, ...)

        Args:
            column_name (str): Name of the column

        Returns:
            int: Index of the column
        """
        try:
            return ord(column_name[0]) - ord("A")
        except ValueError:
            return None

    @classmethod
    def _get_last_used_column(cls):
        """
        Get the last used column index

        Args:
            None

        Returns:
            int: Index of the last used column
        """
        cursor = cls.sheet.createCursor()
        cursor.gotoEndOfUsedArea(False)
        return cursor.RangeAddress.EndColumn

    @classmethod
    def _get_last_used_row(cls):
        """
        Get the last used row index

        Args:
            None

        Returns:
            int: Index of the last used row
        """
        cursor = cls.sheet.createCursor()
        cursor.gotoEndOfUsedArea(False)
        return cursor.RangeAddress.EndRow

    @classmethod
    def _column_name_to_index(cls, column_name):
        """
        Convert a column name to a column index.

        Args:
            column_name (str): Column name, such as 'A' or 'AB'.

        Returns:
            int: Zero-based column index.
        """
        column_name = column_name.upper()
        result = 0
        for char in column_name:
            result = result * 26 + (ord(char) - ord("A") + 1)
        return result - 1

    @classmethod
    def get_workbook_info(cls):
        """
        Get workbook information

        Args:
            None

        Returns:
            dict: Workbook information, including file path, file name, sheets and active sheet
        """
        try:
            info = {
                "file_path": cls.doc.getLocation(),
                "file_title": cls.doc.getTitle(),
                "sheets": [],
                "active_sheet": cls.sheet.Name,
            }

            # Get sheets information
            sheets = cls.doc.getSheets()
            info["sheet_count"] = sheets.getCount()

            # Get all sheet names and info
            for i in range(sheets.getCount()):
                sheet = sheets.getByIndex(i)
                cursor = sheet.createCursor()
                cursor.gotoEndOfUsedArea(False)
                end_col = cursor.getRangeAddress().EndColumn
                end_row = cursor.getRangeAddress().EndRow

                sheet_info = {
                    "name": sheet.getName(),
                    "index": i,
                    "visible": sheet.IsVisible,
                    "row_count": end_row + 1,
                    "column_count": end_col + 1,
                }
                info["sheets"].append(sheet_info)

                # Check if this is the active sheet
                if sheet == cls.sheet:
                    info["active_sheet"] = sheet_info

            cls.ret = json.dumps(info, ensure_ascii=False)
            return info

        except Exception as e:
            cls.ret = f"Error: {e}"

    @classmethod
    def env_info(cls, sheet_name=None):
        """
        Get content of the specified or active sheet

        Args:
            sheet_name (str, optional): Name of the sheet to read. If None, uses active sheet

        Returns:
            dict: Sheet information including name, headers and data
        """
        try:
            # Get the target sheet
            if sheet_name is not None:
                sheet = cls.doc.getSheets().getByName(sheet_name)
            else:
                sheet = cls.sheet

            # Create cursor to find used range
            cursor = sheet.createCursor()
            cursor.gotoEndOfUsedArea(False)
            end_col = cursor.getRangeAddress().EndColumn
            end_row = cursor.getRangeAddress().EndRow

            # Generate column headers (A, B, C, ...)
            col_headers = [chr(65 + i) for i in range(end_col + 1)]

            # Get displayed values from cells
            data_array = []
            for row in range(end_row + 1):
                row_data = []
                for col in range(end_col + 1):
                    cell = sheet.getCellByPosition(col, row)
                    row_data.append(cell.getString())
                data_array.append(row_data)

            # Calculate maximum width for each column
            col_widths = [len(header) for header in col_headers]  # Initialize with header lengths
            for row in data_array:
                for i, cell in enumerate(row):
                    col_widths[i] = max(col_widths[i], len(str(cell)))

            # Format the header row
            header_row = "  | " + " | ".join(f"{h:<{w}}" for h, w in zip(col_headers, col_widths)) + " |"
            separator = "--|-" + "-|-".join("-" * w for w in col_widths) + "-|"

            # Format data rows with row numbers
            formatted_rows = []
            for row_idx, row in enumerate(data_array, 1):
                row_str = f"{row_idx:<2}| " + " | ".join(f"{cell:<{w}}" for cell, w in zip(row, col_widths)) + " |"
                formatted_rows.append(row_str)

            # Combine all parts
            formated_data = header_row + "\n" + separator + "\n" + "\n".join(formatted_rows)

            # Get sheet properties
            sheet_info = {
                "name": sheet.getName(),
                "data": formated_data,
                "row_count": end_row + 1,
                "column_count": end_col + 1,
            }

            cls.ret = json.dumps(sheet_info, ensure_ascii=False)
            return sheet_info

        except Exception as e:
            cls.ret = f"Error: {e}"

    @classmethod
    def get_column_data(cls, column_name):
        """
        Get data from the specified column

        Args:
            column_name (str): Name of the column to read

        Returns:
            list: List of values in the specified column
        """
        column_index = cls._get_column_index(column_name)
        if column_index is None:
            return "Column not found"
        last_row = cls._get_last_used_row()
        _range = cls.sheet.getCellRangeByPosition(column_index, 0, column_index, last_row)
        # Get and flatten the data array.
        cls.ret = json.dumps([row[0] for row in _range.getDataArray()], ensure_ascii=False)
        return [row[0] for row in _range.getDataArray()]

    @classmethod
    def switch_active_sheet(cls, sheet_name):
        """
        Switch to the specified sheet and make it active, create if not exist

        Args:
            sheet_name (str): Name of the sheet to switch to or create

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get all sheets.
            sheets = cls.doc.getSheets()

            # Check whether the sheet exists.
            if not sheets.hasByName(sheet_name):
                # Create a new sheet.
                new_sheet = cls.doc.createInstance("com.sun.star.sheet.Spreadsheet")
                sheets.insertByName(sheet_name, new_sheet)

            # Get the target sheet.
            sheet = sheets.getByName(sheet_name)

            # Switch to the target sheet.
            cls.doc.getCurrentController().setActiveSheet(sheet)

            # Update the current sheet reference.
            cls.sheet = sheet
            cls.ret = "Success"
            return True

        except Exception as e:
            cls.ret = f"Error: {e}"
            return False

    @classmethod
    def set_column_values(cls, column_name, data, start_index=2):
        """
        Set data to the specified column

        Args:
            column_name (str): Name of the column to write
            data (list): List of values to write to the column
            start_index (int): The index of the first row to write to, default is 2 (skip the first row)

        Returns:
            bool: True if successful, False otherwise
        """
        # Get the column index.
        column_index = cls._get_column_index(column_name)
        if column_index is None:
            cls.ret = "Column not found"
            return False
        for i, value in enumerate(data):
            cell = cls.sheet.getCellByPosition(column_index, i + start_index - 1)
            if type(value) == float and value.is_integer():
                cell.setNumber(int(value))
            else:
                cell.setString(str(value))
        cls.ret = "Success"
        return True

    @classmethod
    def highlight_range(cls, range_str, color=0xFF0000):
        """
        highlight the specified range with the specified color

        Args:
            range_str (str): Range to highlight, in the format of "A1:B10"
            color (str): Color to highlight with, default is '0xFF0000' (red)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            _range = cls.sheet.getCellRangeByName(range_str)
            _range.CellBackColor = color
            cls.ret = "Success"
            return True
        except:
            cls.ret = "False"
            return False

    @classmethod
    def transpose_range(cls, source_range, target_cell):
        """
        Transpose the specified range and paste it to the target cell

        Args:
            source_range (str): Range to transpose, in the format of "A1:B10"
            target_cell (str): Target cell to paste the transposed data, in the format of "A1"

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            source = cls.sheet.getCellRangeByName(source_range)
            target = cls.sheet.getCellRangeByName(target_cell)

            data = source.getDataArray()
            # Transpose the data.
            transposed_data = list(map(list, zip(*data)))

            # Set the transposed data.
            target_range = cls.sheet.getCellRangeByPosition(
                target.CellAddress.Column,
                target.CellAddress.Row,
                target.CellAddress.Column + len(transposed_data[0]) - 1,
                target.CellAddress.Row + len(transposed_data) - 1,
            )
            target_range.setDataArray(transposed_data)
            cls.ret = "Success"
            return True
        except Exception as e:
            cls.ret = f"Error: {e}"
            return False

    @classmethod
    def export_to_csv(cls):
        """
        Export the current document to a CSV file

        Args:
            None

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the current document URL.
            doc_url = cls.doc.getURL()
            if not doc_url:
                raise ValueError("Document must be saved first")

            # Build the CSV file path.
            if doc_url.startswith("file://"):
                base_path = doc_url[7:]  # Remove the file:// prefix.
            else:
                base_path = doc_url

            # Get the base path and file name.
            csv_path = os.path.splitext(base_path)[0] + ".csv"

            # Ensure the path is absolute.
            csv_path = os.path.abspath(csv_path)

            # Convert to LibreOffice URL format.
            csv_url = uno.systemPathToFileUrl(csv_path)

            # Set CSV export options.
            props = (
                PropertyValue(Name="FilterName", Value="Text - txt - csv (StarCalc)"),
                PropertyValue(
                    Name="FilterOptions", Value="44,0,76,0"
                ),  # 44=comma, 34=quote, 76=UTF-8, 1=first row as header
            )

            # Export the file.
            cls.doc.storeToURL(csv_url, props)
            cls.ret = "Success"
            return True

        except Exception as e:
            cls.ret = f"Error: {e}"
            return False

    @classmethod
    def sort_column(cls, column_name, ascending=True, start_index=2):
        """
        Sorts the data in the specified column in ascending or descending order

        Args:
            column_name (str): The name of the column to sort (e.g. 'A') or the title
            ascending (bool): Whether to sort in ascending order (default True)
            start_index (int): The index of the first row to sort, default is 1

        Returns:
            bool: True if successful, False otherwise
        """

        try:
            column_data = cls.get_column_data(column_name)[start_index - 1 :]
            column_data = sorted(column_data, key=lambda x: float(x), reverse=not ascending)
        except:
            cls.ret = "Error: Invalid column name or data type"
            return False

        return cls.set_column_values(column_name, column_data, start_index)

    @classmethod
    def set_validation_list(cls, column_name, values):
        """
        Set a validation list for the specified column

        Args:
            column_name (str): The name of the column to set the validation list for
            values (list): The list of values to use for the validation list

        Returns:
            None
        """
        try:
            column_index = cls._get_column_index(column_name)
            last_row = cls._get_last_used_row()
            cell_range = cls.sheet.getCellRangeByPosition(column_index, 1, column_index, last_row)

            # Get the existing validation object.
            validation = cell_range.getPropertyValue("Validation")

            # Set the basic validation type.
            validation.Type = uno.Enum("com.sun.star.sheet.ValidationType", "LIST")
            validation.Operator = uno.Enum("com.sun.star.sheet.ConditionOperator", "EQUAL")

            # Set the dropdown list.
            validation.ShowList = True
            values_str = ";".join(str(val) for val in values)
            validation.Formula1 = values_str

            # Apply validation settings to the cell range.
            cell_range.setPropertyValue("Validation", validation)

            cls.ret = "Success"
            return True

        except Exception as e:
            cls.ret = f"Error: {e}"
            return False

    @classmethod
    def hide_row_data(cls, value="N/A"):
        """
        Hide rows that contain the specified value

        Args:
            value (str): The value to hide rows for, default is 'N/A'

        Returns:
            None
        """
        last_row = cls._get_last_used_row()
        last_col = cls._get_last_used_column()

        for row in range(1, last_row + 1):
            has_value = False
            for col in range(last_col + 1):
                cell = cls.sheet.getCellByPosition(col, row)
                if cell.getString() == value:
                    has_value = True
                    break
            row_range = cls.sheet.getRows().getByIndex(row)
            row_range.IsVisible = not has_value

        cls.ret = "Success"
        return True

    @classmethod
    def reorder_columns(cls, column_order):
        """
        Reorder the columns in the sheet according to the specified order

        Args:
            column_order (list): A list of column names in the desired order

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the new column index.
            new_indices = [cls._get_column_index(col) for col in column_order]

            # Build the new column order.
            for new_index, old_index in enumerate(new_indices):
                if new_index != old_index:
                    cls.sheet.Columns.insertByIndex(new_index, 1)
                    source = cls.sheet.Columns[old_index + (old_index > new_index)]
                    target = cls.sheet.Columns[new_index]
                    target.setDataArray(source.getDataArray())
                    cls.sheet.Columns.removeByIndex(old_index + (old_index > new_index), 1)
            cls.ret = "Success"
            return True

        except Exception as e:
            cls.ret = f"Error: {e}"
            return False

    @classmethod
    def create_pivot_table(
        cls,
        source_sheet,
        table_name,
        row_fields=None,
        col_fields=None,
        value_fields=None,
        aggregation_function="sum",
        target_cell="A1",
    ):
        """
        Create a pivot table in the active worksheet based on data from the active sheet.
        """
        try:
            source = cls.doc.getSheets().getByName(source_sheet)

            # Get the data range.
            cursor = source.createCursor()
            cursor.gotoEndOfUsedArea(False)
            end_col = cursor.getRangeAddress().EndColumn
            end_row = cursor.getRangeAddress().EndRow

            # Get the full data range.
            source_range = source.getCellRangeByPosition(0, 0, end_col, end_row)

            # Get the pivot table collection.
            dp_tables = cls.sheet.getDataPilotTables()

            # Create a pivot table descriptor.
            dp_descriptor = dp_tables.createDataPilotDescriptor()

            # Set the data source.
            dp_descriptor.setSourceRange(source_range.getRangeAddress())

            # Set row fields.
            if row_fields:
                for field in row_fields:
                    field_index = cls._get_column_index(field)
                    dimension = dp_descriptor.getDataPilotFields().getByIndex(field_index)
                    dimension.Orientation = uno.Enum("com.sun.star.sheet.DataPilotFieldOrientation", "ROW")

            # Set column fields.
            if col_fields:
                for field in col_fields:
                    field_index = cls._get_column_index(field)
                    dimension = dp_descriptor.getDataPilotFields().getByIndex(field_index)
                    dimension.Orientation = uno.Enum("com.sun.star.sheet.DataPilotFieldOrientation", "COLUMN")

            # Set data fields.
            for field in value_fields:
                field_index = cls._get_column_index(field)
                dimension = dp_descriptor.getDataPilotFields().getByIndex(field_index)
                dimension.Orientation = uno.Enum("com.sun.star.sheet.DataPilotFieldOrientation", "DATA")

                # Set the aggregation function.
                function_map = {"Count": "COUNT", "Sum": "SUM", "Average": "AVERAGE", "Min": "MIN", "Max": "MAX"}

                if aggregation_function in function_map:
                    dimension.Function = uno.Enum(
                        "com.sun.star.sheet.GeneralFunction", function_map[aggregation_function]
                    )

            # Create the pivot table in the current sheet.
            dp_tables.insertNewByName(
                table_name,  # Pivot table name.
                cls.sheet.getCellRangeByName(target_cell).CellAddress,  # Target location.
                dp_descriptor,  # Descriptor.
            )

            cls.ret = "Success"
            return True
        except Exception as e:
            cls.ret = f"Error: {e}"
            return False

    @classmethod
    def merge_cells(cls, range_str):
        """
        Merge the specified cell range in the active sheet.

        Args:
            range_str (str): Cell range to merge, such as 'A1:B10'.

        Returns:
            bool: True on success, False on failure.
        """
        try:
            # Get the active sheet.
            sheet = cls.sheet

            # Get the cell range.
            cell_range = sheet.getCellRangeByName(range_str)

            # Get the cell range properties.
            range_props = cell_range.getIsMerged()

            # Merge the cell range if it is not already merged.
            if not range_props:
                cell_range.merge(True)

            cls.ret = "Success"
            return True
        except Exception as e:
            cls.ret = f"Error: {e}"
            return False

    @classmethod
    def set_cell_value(cls, cell, value):
        """
        Set a value to a specific cell in the active worksheet.

        Args:
            cell (str): Cell reference (e.g., 'A1')
            value (str): Value to set in the cell

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the cell object.
            cell_obj = cls.sheet.getCellRangeByName(cell)

            if isinstance(value, str) and value.startswith("="):
                # Set the formula.
                cell_obj.Formula = value
                cls.ret = "Success"
                return True

            # Try to convert the value to a number.
            try:
                # Try converting to an integer.
                int_value = int(value)
                cell_obj.Value = int_value
            except ValueError:
                try:
                    # Try converting to a float.
                    float_value = float(value)
                    cell_obj.Value = float_value
                except ValueError:
                    # If it is not numeric, store it as a string.
                    cell_obj.String = value

            cls.ret = "Success"
            return True
        except Exception as e:
            cls.ret = f"Error: {e}"
            return False

    @classmethod
    def format_range(cls, range_str, background_color=None, font_color=None, bold=None, alignment=None):
        """
        Apply formatting to the specified range in the active worksheet

        Args:
            range_str (str): Range to format, in the format of 'A1:B10'
            background_color (str, optional): Background color in hex format (e.g., '#0000ff')
            font_color (str, optional): Font color in hex format (e.g., '#ffffff')
            bold (bool, optional): Whether to make the text bold
            italic (bool, optional): Whether to make the text italic
            alignment (str, optional): Text alignment (left, center, right)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the specified range.
            cell_range = cls.sheet.getCellRangeByName(range_str)

            # Set the background color.
            if background_color:
                # Convert the hexadecimal color to an integer.
                bg_color_int = int(background_color.replace("#", ""), 16)
                cell_range.CellBackColor = bg_color_int

            # Set the font color.
            if font_color:
                # Convert the hexadecimal color to an integer.
                font_color_int = int(font_color.replace("#", ""), 16)
                cell_range.CharColor = font_color_int

            # Set bold formatting.
            if bold is not None:
                cell_range.CharWeight = 150.0 if bold else 100.0  # 150.0 is bold; 100.0 is normal.

            # Set alignment.
            if alignment:
                # Set horizontal alignment.
                struct = cell_range.getPropertyValue("HoriJustify")
                if alignment == "left":
                    struct.value = "LEFT"
                elif alignment == "center":
                    struct.value = "CENTER"
                elif alignment == "right":
                    struct.value = "RIGHT"
                cell_range.setPropertyValue("HoriJustify", struct)

            cls.ret = "Success"
            return True
        except Exception as e:
            cls.ret = f"Error: {e}"
            return False

    @classmethod
    def create_chart(cls, chart_type, data_range, title=None, x_axis_title=None, y_axis_title=None):
        """
        Create a chart in the active worksheet based on the specified data range.

        Args:
            chart_type (str): Type of chart to create (bar, column, line, pie, scatter, area)
            data_range (str): Range containing the data for the chart, in the format of 'A1:B10'
            title (str, optional): Title for the chart
            x_axis_title (str, optional): Title for the X axis
            y_axis_title (str, optional): Title for the Y axis

        Returns:
            bool: True if successful, False otherwise
        """
        # Map chart types to LibreOffice chart constants.
        try:
            chart_type_map = {
                "bar": "com.sun.star.chart.BarDiagram",
                "column": "com.sun.star.chart.ColumnDiagram",
                "line": "com.sun.star.chart.LineDiagram",
                "pie": "com.sun.star.chart.PieDiagram",
                "scatter": "com.sun.star.chart.ScatterDiagram",
                "area": "com.sun.star.chart.AreaDiagram",
            }

            # Get the data range.
            cell_range_address = cls.sheet.getCellRangeByName(data_range).getRangeAddress()

            # Create the chart.
            charts = cls.sheet.getCharts()
            rect = uno.createUnoStruct("com.sun.star.awt.Rectangle")
            rect.Width = 10000  # Default width.
            rect.Height = 7000  # Default height.

            # Add the chart to the sheet.
            charts.addNewByName("MyChart", rect, (cell_range_address,), False, False)

            # Get the chart.
            chart = charts.getByName("MyChart")
            chart_doc = chart.getEmbeddedObject()

            # Set the chart type.
            diagram = chart_doc.createInstance(chart_type_map[chart_type])
            chart_doc.setDiagram(diagram)

            # Set the chart title.
            if title:
                chart_doc.Title.String = title

            # Set the X-axis title.
            if x_axis_title:
                chart_doc.Diagram.XAxis.AxisTitle.String = x_axis_title

            # Set the Y-axis title.
            if y_axis_title:
                chart_doc.Diagram.YAxis.AxisTitle.String = y_axis_title

            cls.ret = "Success"
            return True

        except Exception as e:
            cls.ret = f"Error: {e}"
            return False

    @classmethod
    def freeze_panes(cls, rows=0, columns=0):
        """
        Freeze rows and/or columns in the active sheet.

        Args:
            rows (int): Number of rows to freeze from the top.
            columns (int): Number of columns to freeze from the left.

        Returns:
            bool: True on success, False on failure.
        """
        try:
            # Get the current view.
            view = cls.doc.getCurrentController()

            # Set frozen panes.
            view.freezeAtPosition(columns, rows)

            cls.ret = "Success"
            return True
        except Exception as e:
            cls.ret = f"Error: {e}"
            return False

    @classmethod
    def rename_sheet(cls, old_name, new_name):
        """
        Rename a sheet.

        Args:
            old_name (str): Current name of the sheet to rename.
            new_name (str): New sheet name.

        Returns:
            bool: True on success, False on failure.
        """
        try:
            # Get all sheets.
            sheets = cls.doc.getSheets()

            # Check whether the original sheet exists.
            if not sheets.hasByName(old_name):
                return False

            # Check whether the new name already exists.
            if sheets.hasByName(new_name):
                return False

            # Get the sheet to rename.
            sheet = sheets.getByName(old_name)

            # Rename the sheet.
            sheet.setName(new_name)

            cls.ret = "Success"
            return True

        except Exception as e:
            cls.ret = f"Error: {e}"
            return False

    @classmethod
    def copy_sheet(cls, source_sheet, new_sheet_name=None):
        """
        Create a copy of an existing sheet in the workbook.

        Args:
            source_sheet (str): Name of the sheet to copy.
            new_sheet_name (str, optional): Name of the copied sheet, generated automatically if omitted.

        Returns:
            str: Name of the new sheet, or None on failure.
        """
        try:
            # Get all sheets.
            sheets = cls.doc.getSheets()

            # Check whether the source sheet exists.
            if not sheets.hasByName(source_sheet):
                return None

            # Generate a new name if none was provided.
            if not new_sheet_name:
                # Generate a name such as Sheet1 (2).
                base_name = source_sheet
                counter = 1
                new_sheet_name = f"{base_name} ({counter})"

                # Ensure the name is unique.
                while sheets.hasByName(new_sheet_name):
                    counter += 1
                    new_sheet_name = f"{base_name} ({counter})"

            # Check whether the new name already exists.
            if sheets.hasByName(new_sheet_name):
                return None  # The name already exists; cannot create the sheet.

            # Get the source sheet index.
            source_index = -1
            for i in range(sheets.getCount()):
                if sheets.getByIndex(i).getName() == source_sheet:
                    source_index = i
                    break

            if source_index == -1:
                return None

            # Copy the sheet.
            sheets.copyByName(source_sheet, new_sheet_name, source_index + 1)

            cls.ret = f"New sheet created: {new_sheet_name}"
            return new_sheet_name

        except Exception as e:
            cls.ret = f"Error: {e}"
            return None

    @classmethod
    def reorder_sheets(cls, sheet_name, position):
        """
        Move a sheet to another position in the workbook.

        Args:
            sheet_name (str): Name of the sheet to move.
            position (int): Target position as a zero-based index.

        Returns:
            bool: True on success, False on failure.
        """
        try:
            # Get all sheets.
            sheets = cls.doc.getSheets()

            # Check whether the sheet exists.
            if not sheets.hasByName(sheet_name):
                return False

            # Get the total sheet count.
            sheet_count = sheets.getCount()

            # Check whether the position is valid.
            if position < 0 or position >= sheet_count:
                return False

            # Get the sheet to move.
            sheet = sheets.getByName(sheet_name)

            # Get the current sheet index.
            current_index = -1
            for i in range(sheet_count):
                if sheets.getByIndex(i).Name == sheet_name:
                    current_index = i
                    break

            if current_index == -1:
                return False

            # Move the sheet to the specified position.
            sheets.moveByName(sheet_name, position)

            cls.ret = "Success"
            return True

        except Exception as e:
            cls.ret = f"Error: {e}"
            return False

    @classmethod
    def set_chart_legend_position(cls, position):
        """
        Set the position of the legend in a chart in the active worksheet.

        Args:
            position (str): Position of the legend ('top', 'bottom', 'left', 'right', 'none')

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get all charts in the current sheet.
            charts = cls.sheet.getCharts()
            if charts.getCount() == 0:
                return False

            # Get the first chart, which is the chart to modify.
            chart = charts.getByIndex(0)
            chart_obj = chart.getEmbeddedObject()

            # Get the chart legend.
            diagram = chart_obj.getDiagram()
            legend = chart_obj.getLegend()

            # Apply the requested legend position.
            if position == "none":
                # Hide the legend when none is selected.
                chart_obj.HasLegend = False
            else:
                # Ensure the legend is visible.
                chart_obj.HasLegend = True

                import inspect

                print(inspect.getmembers(legend))

                # Set the legend position.
                if position == "top":
                    pos = uno.Enum("com.sun.star.chart.ChartLegendPosition", "TOP")
                elif position == "bottom":
                    pos = uno.Enum("com.sun.star.chart.ChartLegendPosition", "BOTTOM")
                elif position == "left":
                    pos = uno.Enum("com.sun.star.chart.ChartLegendPosition", "LEFT")
                elif position == "right":
                    pos = uno.Enum("com.sun.star.chart.ChartLegendPosition", "RIGHT")

                legend.Alignment = pos

            cls.ret = "Success"
            return True
        except Exception:
            cls.ret = "Error"
            return False

    @classmethod
    def set_number_format(cls, range_str, format_type, decimal_places=None):
        """
        Apply a specific number format to a range of cells in the active worksheet.

        Args:
            range_str (str): Range to format, in the format of 'A1:B10'
            format_type (str): Type of number format to apply
            decimal_places (int, optional): Number of decimal places to display

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the cell range.
            cell_range = cls.sheet.getCellRangeByName(range_str)

            # Get the number-formatting service.
            number_formats = cls.doc.NumberFormats
            locale = cls.doc.CharLocale

            # Choose the format string for the requested format type.
            format_string = ""

            if format_type == "general":
                format_string = "General"
            elif format_type == "number":
                if decimal_places is not None:
                    format_string = f"0{('.' + '0' * decimal_places) if decimal_places > 0 else ''}"
                else:
                    format_string = "0"
            elif format_type == "currency":
                if decimal_places is not None:
                    format_string = f"[$¥-804]#,##0{('.' + '0' * decimal_places) if decimal_places > 0 else ''}"
                else:
                    format_string = "[$¥-804]#,##0.00"
            elif format_type == "accounting":
                if decimal_places is not None:
                    format_string = f"_-[$¥-804]* #,##0{('.' + '0' * decimal_places) if decimal_places > 0 else ''}_-;-[$¥-804]* #,##0{('.' + '0' * decimal_places) if decimal_places > 0 else ''}_-;_-[$¥-804]* \"-\"_-;_-@_-"
                else:
                    format_string = '_-[$¥-804]* #,##0.00_-;-[$¥-804]* #,##0.00_-;_-[$¥-804]* "-"??_-;_-@_-'
            elif format_type == "date":
                format_string = "YYYY/MM/DD"
            elif format_type == "time":
                format_string = "HH:MM:SS"
            elif format_type == "percentage":
                if decimal_places is not None:
                    format_string = f"0{('.' + '0' * decimal_places) if decimal_places > 0 else ''}%"
                else:
                    format_string = "0.00%"
            elif format_type == "fraction":
                format_string = "# ?/?"
            elif format_type == "scientific":
                if decimal_places is not None:
                    format_string = f"0{('.' + '0' * decimal_places) if decimal_places > 0 else ''}E+00"
                else:
                    format_string = "0.00E+00"
            elif format_type == "text":
                format_string = "@"

            # Get the format key.
            format_key = number_formats.queryKey(format_string, locale, True)

            # Add the format if it does not exist.
            if format_key == -1:
                format_key = number_formats.addNew(format_string, locale)

            # Apply the format.
            cell_range.NumberFormat = format_key

            cls.ret = "Success"
            return True
        except Exception as e:
            cls.ret = f"Error: {e}"
            return False

    @classmethod
    def adjust_column_width(cls, columns, width=None, autofit=False):
        """
        Adjust the widths of specified columns in the active sheet.

        Args:
            columns (str): Column range to adjust; for example, 'A:C' means columns A through C.
            width (float, optional): Desired width in characters.
            autofit (bool, optional): Whether to fit column widths to their contents.

        Returns:
            bool: True on success, False on failure.
        """
        try:
            # Parse the column range.
            col_range = columns.split(":")
            start_col = cls._column_name_to_index(col_range[0])

            if len(col_range) > 1:
                end_col = cls._column_name_to_index(col_range[1])
            else:
                end_col = start_col

            # Get the column objects.
            columns_obj = cls.sheet.getColumns()

            # Iterate over the specified columns.
            for col_idx in range(start_col, end_col + 1):
                column = columns_obj.getByIndex(col_idx)

                if autofit:
                    # Automatically fit column widths.
                    column.OptimalWidth = True
                elif width is not None:
                    # Set the specified width, converted to hundredths of a millimeter.
                    # One character is approximately 256 hundredths of a millimeter wide.
                    column.Width = int(width * 256)

            cls.ret = "Success"
            return True

        except Exception as e:
            cls.ret = f"Error: {e}"
            return False

    @classmethod
    def adjust_row_height(cls, rows, height=None, autofit=False):
        """
        Adjust the heights of specified rows in the active sheet.

        Args:
            rows (str): Row range to adjust; for example, '1:10' means rows 1 through 10.
            height (float, optional): Desired height in points.
            autofit (bool, optional): Whether to fit row heights to their contents.

        Returns:
            bool: True on success, otherwise False.
        """
        try:
            # Parse the row range.
            row_range = rows.split(":")
            start_row = int(row_range[0])
            end_row = int(row_range[1]) if len(row_range) > 1 else start_row

            # Get the row objects.
            for row_index in range(start_row, end_row + 1):
                row = cls.sheet.getRows().getByIndex(row_index - 1)  # Indices are zero-based.

                if autofit:
                    # Automatically fit row heights to the content.
                    row.OptimalHeight = True
                elif height is not None:
                    # Convert the specified height from points to LibreOffice hundredths of a millimeter.
                    # One point is approximately 35.28 hundredths of a millimeter.
                    row.Height = int(height * 35.28)
                    row.OptimalHeight = False

            cls.ret = "Success"
            return True
        except Exception as e:
            cls.ret = f"Error: {e}"
            return False

    @classmethod
    def export_to_pdf(cls, file_path=None, sheets=None, open_after_export=False):
        """
        Export the current document or selected sheets to a PDF file.

        Args:
            file_path (str, optional): PDF output path; defaults to the current document path.
            sheets (list, optional): Sheet names to include in the PDF; defaults to all sheets.
            open_after_export (bool, optional): Whether to open the PDF after export.

        Returns:
            bool: True on success, False on failure.
        """
        try:
            # If no path is specified, use the current document path with a .pdf extension.
            if not file_path:
                if cls.doc.hasLocation():
                    url = cls.doc.getLocation()
                    file_path = uno.fileUrlToSystemPath(url)
                    file_path = os.path.splitext(file_path)[0] + ".pdf"
                else:
                    # If the document is unsaved, create a temporary file on the desktop.
                    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                    file_path = os.path.join(desktop_path, "LibreOffice_Export.pdf")

            # Ensure this is a system path, then convert it to a URL.
            pdf_url = uno.systemPathToFileUrl(os.path.abspath(file_path))

            # Create export properties.
            export_props = []

            # Set the filter name.
            export_props.append(PropertyValue(Name="FilterName", Value="calc_pdf_Export"))

            # If sheets were specified, export only those sheets.
            if sheets and isinstance(sheets, list) and len(sheets) > 0:
                # Get all sheets.
                all_sheets = cls.doc.getSheets()
                selection = []

                # Find the specified sheets.
                for sheet_name in sheets:
                    if all_sheets.hasByName(sheet_name):
                        sheet = all_sheets.getByName(sheet_name)
                        selection.append(sheet)

                # If the sheets were found, set the export selection.
                if selection:
                    export_props.append(PropertyValue(Name="Selection", Value=tuple(selection)))

            # Export the PDF.
            cls.doc.storeToURL(pdf_url, tuple(export_props))

            # Open the PDF after exporting if requested.
            if open_after_export:
                if sys.platform.startswith("darwin"):  # macOS
                    subprocess.call(("open", file_path))
                elif os.name == "nt":  # Windows
                    os.startfile(file_path)
                elif os.name == "posix":  # Linux
                    subprocess.call(("xdg-open", file_path))

            cls.ret = "Success"
            return True

        except Exception as e:
            cls.ret = f"Error: {e}"
            return False

    @classmethod
    def set_zoom_level(cls, zoom_percentage):
        """
        Adjust the current sheet zoom to make cells appear larger or smaller.

        Args:
            zoom_percentage (int): Zoom percentage: 75 means 75%, 100 is normal size, and 150 enlarges the sheet.
                                The usual valid range is 10-400.

        Returns:
            bool: True on success, False on failure.
        """
        try:
            # Get the current controller.
            controller = cls.doc.getCurrentController()

            # Set the zoom value.
            # Keep the zoom value within the supported range.
            if zoom_percentage < 10:
                zoom_percentage = 10
            elif zoom_percentage > 400:
                zoom_percentage = 400

            # Apply the zoom value.
            controller.ZoomValue = zoom_percentage
            cls.ret = "Success"
            return True

        except Exception as e:
            cls.ret = f"Error: {e}"
            return False


if __name__ == "__main__":
    print(CalcTools._get_column_index("A"))
    print(CalcTools.get_workbook_info())
    print(CalcTools.get_content())
    CalcTools.switch_active_sheet("Sheet2")
    # helper.set_column_values('A', [1, 2, 3, 4, 5])
    # helper.highlight_range('A1:A3', 'Red')
    # helper.transpose_range('A1:D5', 'B8')
    print(CalcTools.get_column_data("A"))
    CalcTools.sort_column("A", True)
    CalcTools.hide_row_data("N/A")
    CalcTools.reorder_columns(["B", "A", "C"])
    CalcTools.freeze_panes(1, 1)
    # helper.set_validation_list('C', ['Pass', 'Fail', 'Held'])
    CalcTools.export_to_csv()
