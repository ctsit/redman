.PHONY:
help:
	@echo
	@echo "Available tasks:"
	@echo " stage_green          : copy green sprint template on staging server"
	@echo " stage_brown          : copy brown sprint template on staging server"
	@echo " stage_misc           : copy misc sprint template on staging server"
	@echo " prod_green           : copy green sprint template on production server"
	@echo " prod_brown           : copy brown sprint template on production server"
	@echo " prod_misc            : copy misc sprint template on production server"
	@echo


stage_green:
	fab staging copy_sprint_template_green:is_dry_run=False
stage_brown:
	fab staging copy_sprint_template_brown:is_dry_run=False
stage_misc:
	fab staging copy_sprint_template_misc:is_dry_run=False


prod_green:
	fab production copy_sprint_template_green:is_dry_run=False
prod_brown:
	fab production copy_sprint_template_brown:is_dry_run=False
prod_misc:
	fab production copy_sprint_template_misc:is_dry_run=False


stage_projects:
	fab staging list_projects
prod_projects:
	fab production list_projects


activate:
	. ~/.virtualenvs/redman/bin/activate

test:
	python test_utils.py
