%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from
%distutils.sysconfig import get_python_lib; print (get_python_lib())")}

Name:           kerneltest
Version:        1.2
Release:        1%{?dist}
Summary:        Fedora Kernel test database

License:        GPLv2+
URL:            https://github.com/jmflinuxtx/kerneltest-harness
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python2-devel
BuildRequires:  python-flask
BuildRequires:  python-flask-wtf
BuildRequires:  python-wtforms
BuildRequires:  python-fedora >= 0.3.33
BuildRequires:  python-fedora-flask >= 0.3.33
BuildRequires:  python-openid-teams
BuildRequires:  python-openid-cla
BuildRequires:  python-setuptools

# EPEL6
%if ( 0%{?rhel} && 0%{?rhel} == 6 )
BuildRequires:  python-sqlalchemy0.7
Requires:  python-sqlalchemy0.7
%else
BuildRequires:  python-sqlalchemy > 0.5
Requires:  python-sqlalchemy > 0.5
%endif

Requires:  python-alembic
Requires:  python-flask
Requires:  python-flask-wtf
Requires:  python-wtforms
Requires:  python-kitchen
Requires:  python-fedora >= 0.3.32.3-3
Requires:  python-fedora-flask
Requires:  python-setuptools
Requires:  mod_wsgi

%description
Kerneltests is the application storing the results of kernel tests submitted
either by the Fedora kernel maintainer or Fedora contributors.

%prep
%setup -q

%build
%{__python} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT

# Install apache configuration file
mkdir -p $RPM_BUILD_ROOT/%{_sysconfdir}/httpd/conf.d/
install -m 644 files/kerneltest.conf $RPM_BUILD_ROOT/%{_sysconfdir}/httpd/conf.d/kerneltest.conf

# Install configuration file
mkdir -p $RPM_BUILD_ROOT/%{_sysconfdir}/kerneltest
install -m 644 files/kerneltest.cfg.sample $RPM_BUILD_ROOT/%{_sysconfdir}/kerneltest/kerneltest.cfg


mkdir -p $RPM_BUILD_ROOT/%{_datadir}/kerneltest

# Install WSGI file
install -m 644 files/kerneltest.wsgi $RPM_BUILD_ROOT/%{_datadir}/kerneltest/kerneltest.wsgi

# Install the createdb script
install -m 644 createdb.py $RPM_BUILD_ROOT/%{_datadir}/kerneltest/kerneltest_createdb.py

# Install the alembic configuration file
install -m 644 files/alembic.ini $RPM_BUILD_ROOT/%{_sysconfdir}/kerneltest/alembic.ini

# Install the alembic revisions
cp -r alembic $RPM_BUILD_ROOT/%{_datadir}/kerneltest


%files
%doc README.md LICENSE
%config(noreplace) %{_sysconfdir}/httpd/conf.d/kerneltest.conf
%config(noreplace) %{_sysconfdir}/kerneltest/kerneltest.cfg
%config(noreplace) %{_sysconfdir}/kerneltest/alembic.ini
%dir %{_sysconfdir}/kerneltest/
%{_datadir}/kerneltest/
%{python_sitelib}/kerneltest/
%{python_sitelib}/%{name}*.egg-info


%changelog
* Fri May 19 2017 Pierre-Yves Chibon <pingou@pingoured.fr> - 1.2-1
- Update to 1.2
- Create a Vagrant setup to make developing the app easier (Ryan Lerch)
- Add a warn result separate from fail for 3rd party modules (Justin M. Forbes &
  I)

* Sat Mar 05 2016 Pierre-Yves Chibon <pingou@pingoured.fr> - 1.1.1-1
- Update to 1.1.1
- Fix imports to avoid circular imports
- Increase the size of allowed uploads to max 25Kb by default
- Add fedmenu integration
- Start python3 support

* Fri Nov 07 2014 Pierre-Yves Chibon <pingou@fedoraproject.org> - 1.0.5-1
- Update to 1.0.5
- Log fedmsg tracebacks instead of discarding them
- Don't wait for Rawhide to shut down, it never does
- Remove an unnecessary variable assignment
- Turn the application into a ReverseProxied application

* Wed Jul 02 2014 Justin M. Forbes <jforbes@fedoraproject.org> - 1.0.4-1
- Update to 1.0.4

* Wed Jun 18 2014 Pierre-Yves Chibon <pingou@pingoured.fr> - 1.0.3-1
- Update to 1.0.3

* Tue Jun 17 2014 Pierre-Yves Chibon <pingou@pingoured.fr> - 1.0-1
- Initial packaging work for Fedora
