create table measurements
(
	id int auto_increment,
	thermo_name varchar(20) null,
	time datetime default CURRENT_TIMESTAMP not null,
	actual_temp float null,
	set_temp int null,
	set_program int null,
	relay tinyint null,
	constraint measurements_pk
		primary key (id)
);

create index measurements_thermo_name_index
	on measurements (thermo_name);

