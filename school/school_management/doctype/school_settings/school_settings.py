# Copyright (c) 2026, Havano and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SchoolSettings(Document):
	def onload(self):
		self.ensure_default_comments()
		
	def validate(self):
		self.ensure_default_comments()

	def ensure_default_comments(self):
		o_level_defaults = [
			("10 As & Above", "Excellent work. Maintain this high standard. Aim to achieve A+ in every subject.\nConsult your teachers and other students, and make use of previous exam papers."),
			("9 As", "A hardworking student. Keep up the good work. Aim to get an A in every subject.\nConsult your teachers and other students, and make use of previous exam papers."),
			("7 As - 8 As", "A conscientious student with the potential to do better.\nConsult your teachers and other students, and make use of previous exam papers."),
			("5 Subjects & Above with 4 As", "Satisfactory work, but you need to put more effort in all subjects.\nConsult your teachers and other students, and make use of previous exam papers."),
			("5 Subjects Passed with 3 As", "This is a weak pass. We expect better grades from you.\nConsult your teachers and other students, and make use of previous exam papers."),
			("5 Subjects Passed with 1A - 2As", "This is a weak pass. We expect you to work harder.\nConsult your teachers and other students, and make use of previous exam papers."),
			("5 Subjects Passed without As", "This is a weak pass. You are expected to work harder. Time is running out.\nConsult your teachers and other students, and make use of previous exam papers."),
			("Less than 4 Subjects Passed", "Watch out, time is not on your side. Concentrate on your school work.\nConsult your teachers and other students, and participate in class."),
			("0 Subjects Passed", "A very disappointing end of term report. Please be more serious and understand why you are here.\nConsult your teachers and other students, and make use of previous exam papers.\nParticipate in class and think about your future.")
		]
		
		a_level_defaults = [
			("15+ points", "Excellent work. Maintain this high standard. Aim to achieve 3A*s.\nConsult your teachers and other students, and make use of previous exam papers."),
			("14 points", "A hardworking student. Work on weak areas. Aim for 15 points.\nConsult your teachers and other students, and make use of previous exam papers."),
			("12 - 13 points", "Hardworking student. Aim to get 15 points / 3 A's.\nConsult your teachers and other students, and make use of previous exam papers."),
			("10 - 11 points", "Satisfactory work, but improve in all subjects to get better grades. Aim for 15 points.\nConsult your teachers and other students, and make use of previous exam papers."),
			("8 - 9 points", "This is a weak pass. You should work harder in all subjects.\nConsult your teachers and other students, and make use of previous exam papers."),
			("6 - 7 points", "This is a very weak pass. Put more effort in every subject.\nConsult your teachers and other students, and make use of previous exam papers."),
			("4 - 5 points", "A very disappointing end of term report. Please put in more effort.\nConsult your teachers and other students, and make use of previous exam papers."),
			("0 - 3 points", "A very disappointing end of term. Understand why you are here. Participate in class.\nConsult your teachers and other students, and make use of previous exam papers.")
		]
		primary_defaults = [
			("6 units", "Exceptional. Wonderful work! You are a shining star. Keep up the great effort."),
			("7-12 units", "Outstanding pefomance.  You are doing very well."),
			("13-18 units", "Strong pass, respectable performance. Well done! Keep on working hardand you will do even better."),
			("19-24 units", "Above average, reliable pass. Good work! You are making good progress. Keep believing in yourself and keep trying."),
			("25-36 units", "Standard pass, satisfactory performance. You are doing okay. With a little more practice and focus, you can improve a lot."),
			("37-48 units", "Borderline performance. You have the ability to improve."),
			("49-54 units", "Unsatisfactory results. Please work harder together.")
		]
		
		existing_p_types = [row.comment_type for row in self.get("primary_admin_comments")] if self.get("primary_admin_comments") else []
		for ctype, default_cmt in primary_defaults:
			if ctype not in existing_p_types:
				self.append("primary_admin_comments", {
					"comment_type": ctype,
					"comment": default_cmt
				})
				
		existing_o_types = [row.comment_type for row in self.get("o_level_admin_comments")] if self.get("o_level_admin_comments") else []
		for ctype, default_cmt in o_level_defaults:
			if ctype not in existing_o_types:
				self.append("o_level_admin_comments", {
					"comment_type": ctype,
					"comment": default_cmt
				})
				
		existing_a_types = [row.comment_type for row in self.get("a_level_admin_comments")] if self.get("a_level_admin_comments") else []
		for ctype, default_cmt in a_level_defaults:
			if ctype not in existing_a_types:
				self.append("a_level_admin_comments", {
					"comment_type": ctype,
					"comment": default_cmt
				})
