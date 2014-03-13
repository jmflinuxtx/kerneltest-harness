# Licensed under the terms of the GNU GPL License version 2

CREATE DATABASE kerneltest;

USE kerneltest;

CREATE TABLE kerneltest (
     testid INT NOT NULL AUTO_INCREMENT,
     tester VARCHAR(20) NOT NULL DEFAULT 'anon',
     testdate VARCHAR(80) NOT NULL,
     testset VARCHAR(80) NOT NULL,
     kver VARCHAR(255) NOT NULL,
     fver TINYINT,
     testarch VARCHAR(8) NOT NULL,
     testrel VARCHAR(80) NOT NULL,
     testresult ENUM('PASS', 'FAIL'),
     failedtests TEXT,
     PRIMARY KEY (testid)
);

CREATE TABLE releases (
    releasenum TINYINT NOT NULL,
    support ENUM('RAWHIDE','TEST', 'RELEASE', 'RETIRED')
);

INSERT INTO releases (releasenum, support) VALUES (19, "RELEASE");
INSERT INTO releases (releasenum, support) VALUES (20, "RELEASE");
INSERT INTO releases (releasenum, support) VALUES (21, "RAWHIDE");
