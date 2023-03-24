# -*- coding: utf-8 -*-
# @Time : 2022/3/7 19:18
# @Author : hyx
# @File : page.py
# @desc : web page implement
import json
import time
import os
from urllib.parse import urlparse

import flybirds.core.global_resource as gr
from flybirds.core.global_context import GlobalContext
import flybirds.utils.flybirds_log as log
import flybirds.utils.verify_helper as verify_helper
from flybirds.core.plugin.plugins.default.web.interception import \
    get_case_response_body
from flybirds.utils import dsl_helper
from flybirds.utils.dsl_helper import is_number
from flybirds.utils import file_helper

__open__ = ["Page"]


class Page:
    """Web Page Class"""

    name = "web_page"
    instantiation_timing = "plugin"

    def __init__(self):
        page, context = self.init_page()
        self.page = page
        self.context = context

    @staticmethod
    def init_page():
        context = gr.get_value("browser_context")
        if context is None or gr.get_web_info_value("browserExit") is None \
                or gr.get_web_info_value("browserExit") is True:
            context = Page.new_browser_context()
            gr.set_value("browser_context", context)

        page = context.new_page()
        request_interception = gr.get_web_info_value("request_interception",
                                                     True)
        if request_interception:
            page.route("**/*", handle_route)
            # request listening events
            page.on("request", handle_request)
        page.on("console", handle_page_error)

        ele_wait_time = gr.get_frame_config_value("wait_ele_timeout", 30)
        page_render_timeout = gr.get_frame_config_value("page_render_timeout",
                                                        30)
        page.set_default_timeout(float(ele_wait_time) * 1000)
        page.set_default_navigation_timeout(float(page_render_timeout) * 1000)
        return page, context

    @staticmethod
    def new_browser_context():
        browser = gr.get_value('browser')

        operation_module = gr.get_value("projectScript").custom_operation
        context = None
        if operation_module is not None and \
                hasattr(operation_module, "create_browser_context"):
            create_browser_context = getattr(operation_module,
                                             "create_browser_context")
            if create_browser_context is not None:
                context = create_browser_context(browser)
                if context is not None:
                    log.info(
                        '[new_browser_context] successfully get BrowserContext '
                        'from custom operation')
                    return context

        optional_config = Page.get_web_option_config()
        if optional_config is not None:
            context = browser.new_context(**optional_config,
                                          record_video_dir="videos",
                                          ignore_https_errors=True)
        else:
            context = browser.new_context(record_video_dir="videos",
                                          ignore_https_errors=True)

        # add user custom cookies into browser context
        user_cookie = GlobalContext.get_global_cache("cookies")
        if user_cookie is not None:
            #context.clear_cookies()
            context.add_cookies(cookies=user_cookie)
            log.info(f"this is user cookies: {context.cookies()}")
        else:
            log.info(f"user cookies is None")

        return context

    @staticmethod
    def get_web_option_config():
        emulated_device = None
        user_agent = None
        viewport = None
        device_scale_factor = None
        locale = None
        timezone = None
        permissions = None
        geolocation = None
        has_touch = None
        default_browser_type = None
        gl_dict = {}
        if gr.get_web_info_value("emulated_device") is not None:
            playwright = gr.get_value("playwright")
            emulated_device = playwright.devices[
                gr.get_web_info_value("emulated_device")]
        if gr.get_web_info_value("user_agent") is not None:
            user_agent = gr.get_web_info_value("user_agent")
        if gr.get_web_info_value("locale") is not None:
            locale = gr.get_web_info_value("locale")
        if gr.get_web_info_value("timezone") is not None:
            timezone = gr.get_web_info_value("timezone")
        if gr.get_web_info_value("permissions") is not None:
            permissions = gr.get_web_info_value("permissions")
        if gr.get_web_info_value("geolocation") is not None:
            geolocation = gr.get_web_info_value("geolocation")
        if gr.get_web_info_value("width") is not None and gr.get_web_info_value(
                "height"):
            viewport = {'width': gr.get_web_info_value("width"),
                        'height': gr.get_web_info_value(
                            "height")}
        if gr.get_web_info_value("device_scale_factor") is not None:
            device_scale_factor = gr.get_web_info_value("device_scale_factor")

        if gr.get_web_info_value("has_touch") is not None:
            has_touch = gr.get_web_info_value("has_touch")

        if gr.get_web_info_value("default_browser_type") is not None:
            default_browser_type = gr.get_web_info_value("default_browser_type")

        if user_agent is not None:
            gl_dict["user_agent"] = user_agent
        if viewport is not None:
            gl_dict["viewport"] = viewport
        if locale is not None:
            gl_dict["locale"] = locale
        if timezone is not None:
            gl_dict["timezone_id"] = timezone
        if geolocation is not None:
            gl_dict["geolocation"] = geolocation
            if permissions is None:
                permissions = ["geolocation"]
            else:
                if permissions.index("geolocation") < 0:
                    permissions.append("geolocation")
        if permissions is not None:
            gl_dict["permissions"] = permissions
        if device_scale_factor is not None:
            gl_dict["device_scale_factor"] = device_scale_factor
        if has_touch is not None:
            gl_dict["hasTouch"] = has_touch
        if default_browser_type is not None:
            gl_dict["default_browser_type"] = default_browser_type

        if emulated_device is not None:
            gl_dict.update(emulated_device)

        if gl_dict is not None and len(gl_dict) > 0:
            return gl_dict
        else:
            return None

    def evaluateJs(self, context, param):

        # Convert parameter string to dictionary
        param_dict = dsl_helper.params_to_dic(param, "path")

        # Get path from dictionary
        path = param_dict["path"]

        # Specify path and file extension to look for
        path = os.path.join(os.getcwd(), path)

        # Check if path has .js extension
        if (path.find('.js') < 0):
            message = '[path] could not find js'
            raise FlybirdsException(message)
            return

        # Read JavaScript content from file
        jscontent = file_helper.read_file_from_path(path)

        # Split JavaScript content into a list of test cases
        caselist = None
        casename = ''
        priority = ''
        tag = ''
        if "casename" in param_dict.keys():
            casename = param_dict["casename"]

        if "priority" in param_dict.keys():
            priority = param_dict["priority"]

        if "tag" in param_dict.keys():
            tag = param_dict["tag"]

        caselist = split_string(jscontent)
        caseactuallist = []

        # Process each test case and append executable ones to a list
        for case in caselist:
            isadd, outproperty, outValue = process_string(case, casename, priority, tag)
            if isadd:
                caseactuallist.append((isadd, outproperty, outValue))

        # Check if there are any executable test cases in the list
        if len(caseactuallist) == 0:
            message = '[caseactuallist] could not find excuteable case list'
            raise FlybirdsException(message)
            return

        # Execute each executable test case and log the result
        for item in caseactuallist:
            if item[0]:
                try:
                    self.page.evaluate('() => ' + item[2])
                    log.info("evaluate Js Case:", item[1])
                except Exception:
                    message = '[case] excute failed:' + item[1]
                    raise FlybirdsException(item[1])
                    continue

    def navigate(self, context, param):
        operation_module = gr.get_value("projectScript").custom_operation
        page_url = None
        if hasattr(operation_module, "get_page_url"):
            get_page_url = getattr(operation_module,
                                   "get_page_url")
            page_url = get_page_url(param)

        if page_url is not None:
            log.info('[get_page_url] successfully get page_url_value '
                     'from custom operation')
            self.page.goto(page_url)
            return

        param_dict = dsl_helper.params_to_dic(param, "urlKey")
        url_key = param_dict["urlKey"]
        schema_url_value = gr.get_page_schema_url(url_key)

        if "timeout" in param_dict.keys():
            self.page.goto(schema_url_value, timeout=float(param_dict["timeout"]) * 1000)
            return

        self.page.goto(schema_url_value)

    def return_pre_page(self, context):
        self.page.go_back()

    def sleep(self, context, param):
        if is_number(param):
            self.page.wait_for_timeout(float(param) * 1000)
        else:
            log.warn("default wait for timeout!")
            self.page.wait_for_timeout(3 * 1000)

    def cur_page_equal(self, context, param):
        cur_url = self.page.url.split('?')[0]
        if param.startswith(("http", "https")):
            target_url = param.split('?')[0]
        else:
            schema_url = gr.get_page_schema_url(param)
            target_url = schema_url
        verify_helper.text_equal(target_url, cur_url)

    @staticmethod
    def add_cookies(name, value, url):
        if name is not None and value is not None and url is not None:
            user_cookie = [{'name': name, 'value': value, "url": url}]
            context = gr.get_value("browser_context")
            context.add_cookies(cookies=user_cookie)
            log.info(f"set cookie success: {context.cookies()}")
        else:
            log.info(f"set cookie fail, please check param")

    @staticmethod
    def get_cookie(context):
        context = gr.get_value("browser_context")
        cookies = context.cookies()
        log.info(f"get cookie success: {cookies}")
        return cookies

    @staticmethod
    def get_local_storage(context):
        context = gr.get_value("browser_context")
        local_storage = context.storage_state()
        log.info(f"get local storage success: {local_storage['origins']}")
        return local_storage['origins']

    def get_session_storage(self, context):
        session_storage = self.page.evaluate("() => JSON.stringify(sessionStorage)")
        log.info(f"get session storage success: {session_storage}")
        return session_storage


def handle_page_error(msg):
    if hasattr(msg, "type") and msg.type is not None:
        need_log = False
        if msg.type.lower() == "warn":
            need_log = True
        if msg.type.lower() == "error":
            need_log = True
        if need_log:
            if hasattr(msg, "text"):
                log.info(
                    f"=====================page console==================:\n {msg.text}")


def handle_request(request):
    # interception request handle
    parsed_uri = urlparse(request.url)
    operation = parsed_uri.path.split('/')[-1]
    if operation is not None:
        interception_request = gr.get_value('interceptionRequest')
        request_body = interception_request.get(operation)

        if request_body is not None:
            log.info(
                f'[handle_request] start cache service：{operation}')
            current_request_info = {'postData': request.post_data,
                                    'url': request.url,
                                    'updateTimeStamp': int(
                                        round(time.time() * 1000))}
            interception_request[operation] = current_request_info
            gr.set_value("interceptionRequest", interception_request)


def handle_route(route):
    abort_domain_list = gr.get_web_info_value("abort_domain_list", [])
    parsed_uri = urlparse(route.request.url)
    domain = parsed_uri.hostname
    if abort_domain_list and domain in abort_domain_list:
        route.abort()
        return

    resource_type = route.request.resource_type
    if resource_type != 'fetch' and resource_type != 'xhr':
        route.continue_()
        return

    # mock response data
    operation = parsed_uri.path.split('/')[-1]
    mock_case_id = None
    if operation is not None:
        interception_values = gr.get_value('interceptionValues')
        mock_case_id = interception_values.get(operation)
    if mock_case_id:
        mock_body = get_case_response_body(mock_case_id)
        if mock_body:
            if not isinstance(mock_body, str):
                mock_body = json.dumps(mock_body)
            route.fulfill(status=200,
                          content_type="application/json;charset=utf-8",
                          body=mock_body)
    else:
        route.continue_()

def split_string(input_str):
    result = []
    start = input_str.find("/*")# find the index of the first occurrence of '/' in the input string
    # continue to search for the next occurrence of '/*' in the input string
    # until no more occurrences can be found
    while start != -1:
        end = input_str.find("}", start)  # find the index of the first occurrence of '}' after '/*'
        if end != -1:
            result.append(input_str[start:end + 1])  # append the substring enclosed by '/*' and '}' to the result list
            start = input_str.find("/*", end)  # search for the next occurrence of '/*' after the current '}' index
        else:
            break  # if no more '}' character can be found, break out of the loop

    return result

def process_string(input_str, casename, priority, tag):
    # Split input string by newline character
    str_list = input_str.split('\n')

    # Extract first and second line of input string
    s = str_list[0]
    outvalue = str_list[1]

    # Check if input string has case properties defined using /* */
    case_found = True
    if s.startswith('/*') and s.endswith('*/'):
        # Remove /* */ characters from string and split by whitespace
        s = s[2:-2].strip()
        properties = s.split()

        # Loop through each property and check if it matches given input
        for p in properties:
            if casename != '':
                if p.find('casename') > -1:
                    if p.split('=')[1].find(casename) == -1:
                        case_found = False
                        break
            if priority != '':
                if p.find('priority') > -1:
                    if p.split('=')[1].find(priority) == -1:
                        case_found = False
                        break
            if tag != '':
                if p.find('tag') > -1:
                    if p.split('=')[1].find(tag) == -1:
                        case_found = False
                        break
    else:
        # Raise exception if case properties are not defined using /* */
        message = '[Case property] do not sign as /* */'
        output_list = False
        raise FlybirdsException(message)
    return case_found, s, outvalue