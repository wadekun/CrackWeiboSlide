#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import time
from io import BytesIO
from PIL import Image
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from os import listdir

TEMPLATES_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'templates/')


class CrackWeiboSlide():
    def __init__(self, username, password):
        self.url = 'https://passport.weibo.cn/signin/login?entry=mweibo&r=https://m.weibo.cn/'
        self.browser = webdriver.PhantomJS(executable_path='/usr/local/bin/phantomjs')
        self.browser.set_window_size(1050, 840)
        self.wait = WebDriverWait(self.browser, 20)
        self.username = username
        self.password = password

    def __del__(self):
        self.browser.close()

    def open(self):
        """
        打开网页输入用户名密码并点击
        :return: None
        """
        self.browser.get(self.url)
        time.sleep(1)
        username = self.wait.until(EC.presence_of_element_located((By.ID, 'loginName')))
        password = self.wait.until(EC.presence_of_element_located((By.ID, 'loginPassword')))
        submit = self.wait.until(EC.element_to_be_clickable((By.ID, 'loginAction')))
        username.send_keys(self.username)
        password.send_keys(self.password)
        submit.click()

    def get_position(self):
        """
        获取验证码位置
        :return: 验证码位置元组
        """
        try:
            img = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'patt-shadow')))
        except TimeoutException:
            print('未出现验证码')
            self.open()
        time.sleep(2)
        location = img.location
        size = img.size
        top, bottom, left, right = location['y'], location['y'] + size['height'], location['x'], location['x'] + size[
            'width']
        return (top, bottom, left, right)

    def get_screenshot(self):
        """
        获取网页截图
        :return: 截图对象
        """
        screenshot = self.browser.get_screenshot_as_png()
        screenshot = Image.open(BytesIO(screenshot))
        return screenshot

    def get_image(self, name='captcha.png'):
        """
        获取验证码图片
        :return: 图片对象
        """
        top, bottom, left, right = self.get_position()
        print('验证码位置', top, bottom, left, right)
        screenshot = self.get_screenshot()
        captcha = screenshot.crop((left, top, right, bottom))
        captcha.save(name)
        return captcha

    def is_pixel_equal(self, image1, image2, x, y):
        """
        判断两个像素是否相同
        :param image1: 图片1
        :param image2: 图片2
        :param x: 位置x
        :param y: 位置y
        :return: 像素是否相同
        """
        # 取两个图片的像素点
        pixel1 = image1.load()[x, y]
        pixel2 = image2.load()[x, y]
        threshold = 20
        if abs(pixel1[0] - pixel2[0]) < threshold and abs(pixel1[1] - pixel2[1]) < threshold and abs(
                pixel1[2] - pixel2[2]) < threshold:
            return True
        else:
            return False

    def same_image(self, image, template):
        """
        识别相似验证码
        :param image: 待识别验证码
        :param template: 模板
        :return:
        """
        rgba_image = image.convert('RGBA')

        # 相似度阈值
        threshold = 0.99
        count = 0
        for x in range(rgba_image.width):
            for y in range(rgba_image.height):
                # 判断像素是否相同
                if self.is_pixel_equal(rgba_image, template, x, y):
                    count += 1
        result = float(count) / (rgba_image.width * rgba_image.height)
        if result > threshold:
            print('成功匹配')
            return True
        return False

    def detect_image(self, image):
        """
        匹配图片
        :param image: 图片
        :return: 拖动顺序
        """
        for template_name in listdir(TEMPLATES_FOLDER):
            print('正在匹配', template_name)
            template = Image.open(TEMPLATES_FOLDER + template_name)
            if self.same_image(image, template):
                # 返回顺序
                numbers = [int(number) for number in list(template_name.split('.')[0])]
                print('拖动顺序', numbers)
                return numbers

    def move(self, numbers):
        """
        根据顺序拖动
        :param numbers:
        :return:
        """
        # 获得四个按点
        circles = self.browser.find_elements_by_css_selector('.patt-wrap .patt-circ')
        dx = dy = 0
        for index in range(4):
            circle = circles[numbers[index] - 1]
            # 如果是第一次循环
            if index == 0:
                # 点击第一个按点
                ActionChains(self.browser) \
                    .move_to_element_with_offset(circle, circle.size['width'] / 2, circle.size['height'] / 2) \
                    .click_and_hold().perform()
            else:
                # 小幅移动次数
                times = 30
                # 拖动
                for i in range(times):
                    ActionChains(self.browser).move_by_offset(dx / times, dy / times).perform()
                    time.sleep(1 / times)
            # 如果是最后一次循环
            if index == 3:
                # 松开鼠标
                ActionChains(self.browser).release().perform()
            else:
                # 计算下一次偏移
                dx = circles[numbers[index + 1] - 1].location['x'] - circle.location['x']
                dy = circles[numbers[index + 1] - 1].location['y'] - circle.location['y']

    def get_exactly(self, im):
        """ 精确剪切"""
        imin = -1
        imax = -1
        jmin = -1
        jmax = -1
        row = im.size[0]
        col = im.size[1]
        for i in range(row):
            for j in range(col):
                if im.load()[i, j] != 255:
                    imax = i
                    break
            if imax == -1:
                imin = i

        for j in range(col):
            for i in range(row):
                if im.load()[i, j] != 255:
                    jmax = j
                    break
            if jmax == -1:
                jmin = j
        return (imin + 1, jmin + 1, imax + 1, jmax + 1)

    def get_image2(self, name='captcha.png'):
        im0 = Image.open(BytesIO(self.browser.get_screenshot_as_png()))
        im0.save('screenshot.png')
        box = self.browser.find_element_by_id('patternCaptchaHolder')
        im = im0.crop((int(box.location['x']) + 10, int(box.location['y']) + 100,
                       int(box.location['x']) + box.size['width'] - 10,
                       int(box.location['y']) + box.size['height'] - 10)).convert('L')
        newBox = self.get_exactly(im)
        im = im.crop(newBox)
        im.save(name)
        return im

    def get_cookies(self):
        cookie = {}
        for elem in self.browser.get_cookies():
            cookie[elem["name"]] = elem["value"]
        return cookie

    def crack(self):
        """
        破解入口
        :return:
        """
        self.open()
        time.sleep(3.5)
        # 获取验证码图片
        image = self.get_image2('captcha.png')
        numbers = self.detect_image(image)
        self.move(numbers)
        time.sleep(10)
        print('识别结束. cookie: %s' % self.get_cookies()),
        return self.get_cookies()


if __name__ == '__main__':
    crack = CrackWeiboSlide('13414760074', 'lckqwe123.')
    crack.crack()

