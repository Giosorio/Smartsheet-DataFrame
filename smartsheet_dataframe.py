"""
Smartsheet-DataFrame
####################

This package contains functions to retrieve Smartsheet
reports and sheets as a Pandas DataFrame

"""

# TODO: Rewrite SDK obj functions to use .to_dict() and request functions
# TODO: Abstract request portion of request function into sub-function

import pandas as pd
import requests
from typing import Any:
import logging
import warnings
import time


logger = logging.getLogger(__name__)


def get_report_as_df(token: str = None,
                     report_id: int = None,
                     include_row_id: bool = True,
                     include_parent_id: bool = True,
                     report_obj: Any = None) -> pd.DataFrame:
    """
    Get a Smartsheet report as a Pandas DataFrame

    :param token: Smartsheet Personal Access Token
    :param report_id: ID of report to retrieve
    :param include_row_id: Include row IDs in DataFrame
    :param include_parent_id: Include row Parent IDs in DataFrame
    :param report_obj: Smartsheet Python SDK Report object

    :return: Pandas DataFrame with report data
    """

    if (not token and not report_obj) or (token and report_obj):
        raise ValueError("One of 'token' or 'report_obj' must be included in parameters")

    if token and not report_id:
        try:
            import smartsheet.models
            if isinstance(token, smartsheet.models.sheet.Sheet):
                raise ValueError("Function must be called with the 'report_obj=' keyword argument")
        except ModuleNotFoundError:
            raise ValueError("A report_id must be included in the parameters if a token is provided")

    if report_obj and report_id:
        logger.warning("A 'report_id' has been provided along with a 'report_obj' \n" +
                       "The 'sheet_id' parameter will be ignored")

    if token and report_id:
        return _report_to_dataframe(_get_report_from_request(token, report_id), include_row_id, include_parent_id)
    elif report_obj:
        return _report_to_dataframe(report_obj.to_dict(), include_row_id, include_parent_id)


def get_sheet_as_df(token: str = None,
                    sheet_id: int = None,
                    include_row_id: bool = True,
                    include_parent_id: bool = True,
                    sheet_obj: Any = None) -> pd.DataFrame:
    """
    Get a Smartsheet sheet as a Pandas DataFrame

    :param token: Smartsheet Personal Authentication Token
    :param sheet_id: Smartsheet source sheet ID to get
    :param include_row_id: Include row IDs in DataFrame
    :param include_parent_id: Include row Parent IDs in DataFrame
    :param sheet_obj: Smartsheet Python SDK sheet object

    :return: Pandas DataFrame with sheet data
    """

    if (not token and not sheet_obj) or (token and sheet_obj):
        raise ValueError("One of 'token' or 'sheet_obj' must be included in parameters")

    if token and not sheet_id:
        try:
            import smartsheet.models
            if isinstance(token, smartsheet.models.sheet.Sheet):
                raise ValueError("Function must be called with the 'sheet_obj=' keyword argument")
        except ModuleNotFoundError:
            raise ValueError("A sheet_id must be included in the parameters if a token is provided")

    if sheet_obj and sheet_id:
        logger.warning("A 'sheet_id' has been provided along with a 'sheet_obj' \n" +
                       "The 'sheet_id' parameter will be ignored")

    if token and sheet_id:
        return _sheet_to_dataframe(_get_sheet_from_request(token, sheet_id), include_row_id, include_parent_id)
    elif sheet_obj:
        return _sheet_to_dataframe(sheet_obj.to_dict(), include_row_id, include_parent_id)


def get_as_df(type: str,
              token: str = None,
              id: int = None,
              obj: Any = None,
              include_row_id: bool = True,
              include_parent_id: bool = True) -> pd.DataFrame:
    if (not token and not obj) or (token and obj):
        raise ValueError("One of 'token' or 'obj' must be included in parameters")

    if token and not id:
        try:
            import smartsheet.models
            if isinstance(token, smartsheet.models.sheet.Sheet):
                raise ValueError("Function must be called with the 'sheet_obj=' keyword argument")
        except ModuleNotFoundError:
            raise ValueError("A sheet_id must be included in the parameters if a token is provided")

    if obj and id:
        logger.warning("An 'id' has been provided along with a 'obj' \n" +
                       "The 'id' parameter will be ignored")

    if token and id:
        if type.upper() == "SHEET":
            return _get_sheet_from_request(token, id, include_row_id, include_parent_id)
        elif type.upper() == "REPORT":
            return _get_sheet_from_request(token, id, include_row_id, include_parent_id)
    elif obj:
        if type.upper() == "SHEET":
            pass
            # return _get_sheet_from_sdk_obj(obj, include_row_id, include_parent_id)
        elif type.upper() == "REPORT":
            pass
            # return _get_report_from_sdk_obj(obj, include_row_id, include_parent_id)


# TODO: Include Multi-Contact List emails
def _get_sheet_from_request(token: str, sheet_id: int) -> dict:
    credentials: dict = {"Authorization": f"Bearer {token}"}
    response = _do_request(f"https://api.smartsheet.com/2.0/sheets/{sheet_id}?include=objectValue&level=1",
                           options=credentials)

    return response.json()


def _get_report_from_request(token: str, report_id: int) -> dict:
    credentials: dict = {"Authorization": f"Bearer {token}"}
    response = _do_request(f"https://api.smartsheet.com/2.0/reports/{report_id}?pageSize=50000", options=credentials)

    return response.json()


def _sheet_to_dataframe(sheet_dict: dict, include_row_id: bool = True, include_parent_id: bool = True) -> pd.DataFrame:

    columns_list = [column['title'] for column in sheet_dict['columns']]

    if include_parent_id:
        columns_list.insert(0, "parent_id")
    if include_row_id:
        columns_list.insert(0, "row_id")

    rows_list = []
    for row in sheet_dict['rows']:
        cells_list = []
        if include_row_id:
            cells_list.append(int(row['id']))
        if include_parent_id:
            cells_list.append(int(row['parentId'])) if 'parentId' in row else cells_list.append('')

        for cell in row['cells']:
            if 'value' in cell:
                cells_list.append(cell['value'])
            elif 'objectValue' in cell:
                cells_list.append(_handle_object_value(cell['objectValue']))
            else:
                cells_list.append('')
        else:
            rows_list.append(cells_list)

    return pd.DataFrame(rows_list, columns=columns_list)


def _report_to_dataframe(report_dict: dict, include_row_id: bool, include_parent_id: bool) -> pd.DataFrame:

    columns_list = [column['title'] for column in report_dict['columns']]

    if include_parent_id:
        columns_list.insert(0, "parent_id")
    if include_row_id:
        columns_list.insert(0, "row_id")

    rows_list = []
    for row in report_dict['rows']:
        cells_list = []
        if include_row_id: cells_list.append(int(row['id']))
        if include_parent_id:
            cells_list.append(int(row['parentId'])) if 'parentId' in row else cells_list.append('')
        for cell in row['cells']:
            if row['id'] not in cells_list:
                if include_row_id:
                    cells_list.append(int(row['id']))
                if include_parent_id:
                    if 'parentId' in row:
                        cells_list.append(int(row['parentId']))

            if 'value' in cell:
                cells_list.append(cell['value'])
            else:
                cells_list.append('')
        else:
            rows_list.append(cells_list)

    return pd.DataFrame(rows_list, columns=columns_list)


def _do_request(url: str, options: dict, retries: int = 3) -> requests.Response:
    i = 0
    for i in range(retries):
        try:
            response = requests.get(url, headers=options)
            response_json = response.json()

            if response.status_code != 200:
                if response_json['errorCode'] == 1002 or response_json['errorCode'] == 1003 or \
                        response_json['errorCode'] == 1004:
                    raise AuthenticationError("Could not connect using the supplied auth token \n" +
                                              response.text)
                elif response_json['errorCode'] == 4004:
                    logger.debug(f"Rate limit exceeded. Waiting and trying again... {i}")
                    time.sleep(5 + (i * 5))
                    continue
                else:
                    warnings.warn("An unhandled status_code was returned by the Smartsheet API: \n" +
                                  response.text)
                    return
        except AuthenticationError:
            logger.exception("Smartsheet returned an error status code")
            break
        except:
            logger.exception(f"Not able to retrieve get response. Retrying... {i}")
            time.sleep(5 + (i * 5))
            continue
        break
    else:
        raise Exception(f"Could not retrieve request after retrying {i} times")

    return response


def _handle_object_value(object_value: Any) -> str:
    email_list_string: str = ""
    if object_value['objectType'].upper() == "MULTI_CONTACT":
        email_list_string = ', '.join(obj['email'] for obj in object_value['values'])

    return email_list_string


class AuthenticationError(Exception):
    pass
