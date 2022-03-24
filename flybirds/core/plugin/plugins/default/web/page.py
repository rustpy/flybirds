# -*- coding: utf-8 -*-
# @Time : 2022/3/7 19:18
# @Author : hyx
# @File : page.py
# @desc : web page implement
import flybirds.core.global_resource as global_resource
import flybirds.core.global_resource as gr
import flybirds.utils.flybirds_log as log
from flybirds.utils import dsl_helper
from flybirds.utils.dsl_helper import is_number

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
        browser = gr.get_value('browser')
        context = browser.new_context(record_video_dir="videos")
        default_timeout = gr.get_web_info_value("web_time_out", 30)
        context.set_default_timeout(float(default_timeout) * 1000)
        page = context.new_page()
        return page, context

    def navigate(self, context, param):
        param_dict = dsl_helper.params_to_dic(param, "urlKey")
        url_key = param_dict["urlKey"]
        schema_url_value = gr.get_page_schema_url(url_key)
        self.page.goto(schema_url_value)

    def return_pre_page(self, context):
        self.page.go_back()

    def sleep(self, context, param):
        if is_number(param):
            self.page.wait_for_timeout(float(param) * 1000)
        else:
            log.warn(f"default wait for timeout!")
            self.page.wait_for_timeout(3 * 1000)

    def cur_page_equal(self, context, param):
        cur_url = self.page.url
        if param.startswith(("http", "https")):
            return param == cur_url
        schema_url = global_resource.get_page_schema_url(param)
        return schema_url == cur_url
